#!/usr/bin/env python3
"""Focused regression test for SMTP credential sending password-safety bug.

Verifies that /api/config/send-credentials/{user_id} and
/api/config/send-credentials-bulk do not mutate stored password hashes when SMTP
is disabled, incomplete, or delivery fails.
"""
import copy
import json
import os
import time
import uuid
from pathlib import Path

import bcrypt
import requests
from pymongo import MongoClient


APP_DIR = Path("/app")
BACKEND_ENV = APP_DIR / "backend" / ".env"
API_BASE = os.environ.get("API_BASE", "http://localhost:8001")
RESULT_PATH = APP_DIR / "test_reports" / "bug_verify_smtp_credentials_safety_results.json"

REQUIRED_USERS = {
    "superadmin": ("lcorreaq@gmail.com", "IUDigital2026"),
    "profesor": ("docente.demo@iudigital.edu.co", "Docente2026"),
    "decano": ("decano.test@iudigital.edu.co", "Decano2026!"),
    "coordinador": ("coord.test@iudigital.edu.co", "Coord2026!"),
    "direccion": ("direccion.test@iudigital.edu.co", "Direccion2026!"),
}


def parse_env(path: Path) -> dict:
    out = {}
    for raw in path.read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        out[k] = v.strip().strip('"').strip("'")
    return out


def make_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def serializable(obj):
    if isinstance(obj, dict):
        return {k: serializable(v) for k, v in obj.items() if k != "_id"}
    if isinstance(obj, list):
        return [serializable(v) for v in obj]
    return obj


class Tester:
    def __init__(self):
        env = parse_env(BACKEND_ENV)
        self.client = MongoClient(env["MONGO_URL"])
        self.db = self.client[env["DB_NAME"]]
        self.session = requests.Session()
        self.token = None
        self.results = []
        self.failures = []
        self.smtp_original_exists = False
        self.smtp_original = None
        self.user_snapshots = {}
        self.temp_ids = []
        self.temp_role = f"qa_smtp_role_{uuid.uuid4().hex[:8]}"

    def record(self, name: str, ok: bool, detail: str, extra=None):
        row = {"name": name, "ok": bool(ok), "detail": detail}
        if extra is not None:
            row["extra"] = serializable(extra)
        self.results.append(row)
        print(("PASS" if ok else "FAIL") + f" - {name}: {detail}")
        if not ok:
            self.failures.append(row)

    def request(self, method: str, path: str, **kwargs):
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        timeout = kwargs.pop("timeout", 45)
        return self.session.request(method, API_BASE + path, headers=headers, timeout=timeout, **kwargs)

    def login(self, email: str, password: str):
        return self.session.post(
            API_BASE + "/api/auth/login",
            json={"email": email, "password": password},
            timeout=20,
        )

    def setup(self):
        root = self.session.get(API_BASE + "/api/", timeout=10)
        self.record("backend health", root.status_code == 200, f"GET /api/ -> {root.status_code}", root.json() if root.headers.get("content-type", "").startswith("application/json") else root.text[:200])

        admin_email, admin_password = REQUIRED_USERS["superadmin"]
        admin_login = self.login(admin_email, admin_password)
        ok = admin_login.status_code == 200 and admin_login.json().get("access_token")
        admin_login_extra = admin_login.json() if admin_login.headers.get("content-type", "").startswith("application/json") else admin_login.text[:200]
        if isinstance(admin_login_extra, dict) and admin_login_extra.get("access_token"):
            admin_login_extra = copy.deepcopy(admin_login_extra)
            admin_login_extra["access_token"] = "[redacted]"
        self.record("superadmin login", ok, f"POST /api/auth/login -> {admin_login.status_code}", admin_login_extra)
        if not ok:
            raise RuntimeError("Cannot authenticate as superadmin; meaningful protected endpoint testing is blocked")
        self.token = admin_login.json()["access_token"]

        smtp_doc = self.db.system_settings.find_one({"_id": "smtp_config"})
        self.smtp_original_exists = smtp_doc is not None
        self.smtp_original = copy.deepcopy(smtp_doc)

        for role, (email, _) in REQUIRED_USERS.items():
            doc = self.db.users.find_one({"email": email})
            self.record(f"required user exists: {role}", doc is not None, email)
            if doc:
                self.user_snapshots[email] = copy.deepcopy(doc)

        for role, (email, password) in REQUIRED_USERS.items():
            resp = self.login(email, password)
            self.record(f"initial login works: {role}", resp.status_code == 200, f"{email} -> {resp.status_code}")

        # Temp users are used for edge cases so real long-lived test credentials are not reset if a regression exists.
        temp_email_id = f"qa-smtp-email-{uuid.uuid4().hex[:10]}"
        temp_email = f"{temp_email_id}@example.test"
        temp_no_email_id = f"qa-smtp-no-email-{uuid.uuid4().hex[:10]}"
        self.temp_email_id = temp_email_id
        self.temp_email = temp_email
        self.temp_no_email_id = temp_no_email_id
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        temp_docs = [
            {
                "id": temp_email_id,
                "email": temp_email,
                "full_name": "QA SMTP Email User",
                "role": self.temp_role,
                "active": True,
                "password": make_hash("OriginalTemp2026!"),
                "must_change_password": False,
                "created_at": now,
            },
            {
                "id": temp_no_email_id,
                "email": "",
                "full_name": "QA SMTP No Email User",
                "role": self.temp_role,
                "active": True,
                "password": make_hash("OriginalTemp2026!"),
                "must_change_password": False,
                "created_at": now,
            },
        ]
        for doc in temp_docs:
            self.db.users.insert_one(copy.deepcopy(doc))
            self.temp_ids.append(doc["id"])
            self.user_snapshots[doc.get("email") or doc["id"]] = copy.deepcopy(doc)
        self.record("temp edge-case users created", True, f"role={self.temp_role}, ids={self.temp_ids}")

    def restore_snapshot_if_changed(self, email_or_id: str, label: str):
        snap = self.user_snapshots[email_or_id]
        key = {"id": snap["id"]}
        current = self.db.users.find_one(key)
        unchanged = current and current.get("password") == snap.get("password")
        self.record(f"password hash unchanged: {label}", unchanged, f"id={snap['id']}")
        if current and current.get("password") != snap.get("password"):
            restore_doc = copy.deepcopy(snap)
            restore_doc.pop("_id", None)
            self.db.users.update_one(key, {"$set": restore_doc})
            self.record(f"restored mutated password snapshot: {label}", True, "cleanup restore performed after detecting mutation")
        return unchanged

    def assert_required_hashes_unchanged(self, context: str):
        all_ok = True
        for role, (email, _) in REQUIRED_USERS.items():
            if email not in self.user_snapshots:
                continue
            snap = self.user_snapshots[email]
            current = self.db.users.find_one({"id": snap["id"]})
            ok = current and current.get("password") == snap.get("password")
            if not ok and current:
                restore_doc = copy.deepcopy(snap)
                restore_doc.pop("_id", None)
                self.db.users.update_one({"id": snap["id"]}, {"$set": restore_doc})
            self.record(f"required hash unchanged after {context}: {role}", ok, email)
            all_ok = all_ok and ok
        return all_ok

    def set_smtp(self, cfg: dict):
        base = {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "smtp_from_name": "QA SMTP Safety",
            "smtp_enabled": False,
        }
        base.update(cfg)
        self.db.system_settings.update_one({"_id": "smtp_config"}, {"$set": base}, upsert=True)
        saved = self.db.system_settings.find_one({"_id": "smtp_config"})
        self.record("smtp config set", True, str({k: saved.get(k) for k in ["smtp_enabled", "smtp_host", "smtp_port", "smtp_user"]}))

    def expect_400_with_no_side_effect_message(self, resp, label):
        try:
            body = resp.json()
            detail = str(body.get("detail", body))
        except Exception:
            detail = resp.text
        ok = resp.status_code == 400 and "No se envió ningún correo ni se modificó ninguna contraseña" in detail
        self.record(label, ok, f"status={resp.status_code}, detail={detail[:300]}", {"status": resp.status_code, "detail": detail})
        return ok

    def run_cases(self):
        prof_doc = self.user_snapshots[REQUIRED_USERS["profesor"][0]]
        prof_id = prof_doc["id"]

        # 1) SMTP disabled: individual endpoint must return 400 and not change password.
        self.set_smtp({"smtp_enabled": False, "smtp_user": "", "smtp_password": ""})
        resp = self.request("POST", f"/api/config/send-credentials/{prof_id}", json={"reset_password": True})
        self.expect_400_with_no_side_effect_message(resp, "individual disabled SMTP returns idempotent 400")
        self.restore_snapshot_if_changed(REQUIRED_USERS["profesor"][0], "profesor after individual disabled SMTP")
        self.record("profesor login after individual disabled SMTP", self.login(*REQUIRED_USERS["profesor"]).status_code == 200, "original password still accepted")

        # 2) SMTP disabled: bulk endpoint with both only_missing modes returns same 400 and changes no required hashes.
        for only_missing in (True, False):
            resp = self.request("POST", "/api/config/send-credentials-bulk", json={"role": "profesor", "only_missing": only_missing, "limit": 1})
            self.expect_400_with_no_side_effect_message(resp, f"bulk disabled SMTP returns idempotent 400 only_missing={only_missing}")
            self.assert_required_hashes_unchanged(f"bulk disabled only_missing={only_missing}")

        # 3) SMTP enabled but smtp_user missing: individual preflight 400, no password change.
        self.set_smtp({"smtp_enabled": True, "smtp_user": "", "smtp_password": "present-app-password"})
        resp = self.request("POST", f"/api/config/send-credentials/{prof_id}", json={"reset_password": True})
        try:
            detail = str(resp.json().get("detail"))
        except Exception:
            detail = resp.text
        self.record("individual enabled SMTP missing user returns 400", resp.status_code == 400 and "Faltan credenciales SMTP" in detail and "No se envió ningún correo ni se modificó ninguna contraseña" in detail, f"status={resp.status_code}, detail={detail[:300]}")
        self.restore_snapshot_if_changed(REQUIRED_USERS["profesor"][0], "profesor after missing smtp_user")

        # 4) SMTP enabled but smtp_password missing: bulk preflight 400, no password change.
        self.set_smtp({"smtp_enabled": True, "smtp_user": "qa-smtp@example.test", "smtp_password": ""})
        resp = self.request("POST", "/api/config/send-credentials-bulk", json={"role": "profesor", "only_missing": False, "limit": 1})
        try:
            detail = str(resp.json().get("detail"))
        except Exception:
            detail = resp.text
        self.record("bulk enabled SMTP missing password returns 400", resp.status_code == 400 and "Faltan credenciales SMTP" in detail and "No se envió ningún correo ni se modificó ninguna contraseña" in detail, f"status={resp.status_code}, detail={detail[:300]}")
        self.assert_required_hashes_unchanged("bulk missing smtp_password")

        # 5) Nonexistent user and no-email user must not touch existing user passwords.
        resp = self.request("POST", "/api/config/send-credentials/nonexistent-qa-user", json={"reset_password": True})
        self.record("individual nonexistent user returns 404", resp.status_code == 404, f"status={resp.status_code}, body={resp.text[:200]}")
        resp = self.request("POST", f"/api/config/send-credentials/{self.temp_no_email_id}", json={"reset_password": True})
        self.record("individual user without email returns 400", resp.status_code == 400 and "Usuario sin correo" in resp.text, f"status={resp.status_code}, body={resp.text[:200]}")
        self.restore_snapshot_if_changed(self.temp_no_email_id, "temp no-email user")
        self.assert_required_hashes_unchanged("nonexistent/no-email cases")

        # 6) SMTP enabled with syntactically complete but non-working server: send fails after password is generated in memory;
        # password must still not be persisted. Use localhost:1 for a deterministic connection failure and temp users only.
        self.set_smtp({
            "smtp_enabled": True,
            "smtp_host": "127.0.0.1",
            "smtp_port": 1,
            "smtp_user": "qa.invalid.smtp@example.test",
            "smtp_password": "invalid-app-password",
        })
        resp = self.request("POST", f"/api/config/send-credentials/{self.temp_email_id}", json={"reset_password": True}, timeout=45)
        try:
            detail = str(resp.json().get("detail"))
        except Exception:
            detail = resp.text
        self.record("individual complete SMTP but delivery failure returns no-mutation 400", resp.status_code == 400 and "Fallo al enviar correo" in detail and "contraseña no fue modificada" in detail.lower(), f"status={resp.status_code}, detail={detail[:300]}")
        self.restore_snapshot_if_changed(self.temp_email, "temp email user after failed individual send")

        for only_missing in (True, False):
            resp = self.request("POST", "/api/config/send-credentials-bulk", json={"role": self.temp_role, "only_missing": only_missing, "limit": 1}, timeout=45)
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text}
            ok = resp.status_code == 200 and body.get("sent") == 0 and body.get("failed", 0) >= 1
            self.record(f"bulk complete SMTP but delivery failure records failure only_missing={only_missing}", ok, f"status={resp.status_code}, body={serializable(body)}", body)
            self.restore_snapshot_if_changed(self.temp_email, f"temp email user after failed bulk only_missing={only_missing}")

        # Final proof: all required users can still log in with original credentials.
        for role, creds in REQUIRED_USERS.items():
            resp = self.login(*creds)
            self.record(f"final original login still works: {role}", resp.status_code == 200, f"{creds[0]} -> {resp.status_code}")
        self.assert_required_hashes_unchanged("all failed send attempts")

    def cleanup(self):
        for uid in self.temp_ids:
            self.db.users.delete_one({"id": uid})
        if self.smtp_original_exists:
            original = copy.deepcopy(self.smtp_original)
            self.db.system_settings.replace_one({"_id": "smtp_config"}, original, upsert=True)
        else:
            self.db.system_settings.delete_one({"_id": "smtp_config"})
        self.client.close()
        self.record("cleanup completed", True, "restored original smtp_config and removed temp users")

    def write_results(self):
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps({
            "api_base": API_BASE,
            "temp_role": self.temp_role,
            "results": self.results,
            "failures": self.failures,
            "passed": len(self.failures) == 0,
        }, indent=2, ensure_ascii=False))


def main():
    tester = Tester()
    try:
        tester.setup()
        tester.run_cases()
    except Exception as exc:
        tester.record("unexpected exception", False, repr(exc))
    finally:
        try:
            tester.cleanup()
        except Exception as cleanup_exc:
            tester.record("cleanup exception", False, repr(cleanup_exc))
        tester.write_results()
    if tester.failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()