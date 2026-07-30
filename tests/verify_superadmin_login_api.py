#!/usr/bin/env python3
"""Focused API verification for lcorreaq@gmail.com password reset bug."""
import json
import os
from pathlib import Path
from urllib import request, error


APP_DIR = Path("/app")
REPORT_DIR = APP_DIR / "test_reports"
EMAIL = "lcorreaq@gmail.com"
NEW_PASSWORD = "IUDigital2026"
OLD_PASSWORD = "Chocolate2026!"


def load_frontend_base_url():
    env_path = APP_DIR / "frontend" / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")


def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 bug-verification"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8")), dict(resp.headers)
    except error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
        except Exception:
            data = {"raw": ""}
        return exc.code, data, dict(exc.headers)


def get_json(url, token):
    req = request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0 bug-verification"},
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
        except Exception:
            data = {"raw": ""}
        return exc.code, data


def main():
    base = load_frontend_base_url().rstrip("/")
    login_url = f"{base}/api/auth/login"
    me_url = f"{base}/api/auth/me"
    result = {"base_url": base, "checks": {}, "details": {}, "passed": False}

    status_new, data_new, _ = post_json(login_url, {"email": EMAIL, "password": NEW_PASSWORD})
    user = data_new.get("user", {}) if isinstance(data_new, dict) else {}
    token = data_new.get("access_token") if isinstance(data_new, dict) else None
    result["details"]["new_password_status"] = status_new
    result["details"]["new_password_user"] = {k: user.get(k) for k in ["email", "role", "must_change_password"]}
    result["checks"]["new_password_login_200"] = status_new == 200
    result["checks"]["access_token_present"] = isinstance(token, str) and len(token) > 20
    result["checks"]["role_superadmin"] = user.get("role") == "superadmin"
    result["checks"]["must_change_password_false"] = user.get("must_change_password") is False

    status_old, data_old, _ = post_json(login_url, {"email": EMAIL, "password": OLD_PASSWORD})
    result["details"]["old_password_status"] = status_old
    result["details"]["old_password_detail"] = data_old.get("detail") if isinstance(data_old, dict) else data_old
    result["checks"]["old_password_login_401"] = status_old == 401

    if token:
        status_me, data_me = get_json(me_url, token)
        result["details"]["me_status"] = status_me
        result["details"]["me_user"] = {k: data_me.get(k) for k in ["email", "role", "must_change_password"]} if isinstance(data_me, dict) else data_me
        result["checks"]["me_with_token_200"] = status_me == 200
        result["checks"]["me_same_user"] = isinstance(data_me, dict) and data_me.get("email") == EMAIL and data_me.get("role") == "superadmin"
    else:
        result["checks"]["me_with_token_200"] = False
        result["checks"]["me_same_user"] = False

    result["passed"] = all(result["checks"].values())
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "superadmin_login_api_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
