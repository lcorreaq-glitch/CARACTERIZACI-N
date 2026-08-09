"""Backend tests for Tanda 1 new features:
- /api/config/{smtp,ai,overview}
- /api/config/smtp/test (expected 400 SMTP no habilitado)
- /api/config/send-credentials/{user_id} (expected 400 SMTP no habilitado)
- /api/config/send-credentials-bulk (no envío real; comportamiento)
- /api/admin/facultades/{id}/ficha (estructura)
- RBAC: non-superadmin no accede a /config/smtp ni /config/ai
"""
import os
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        v = line.split("=", 1)[1].strip()
                        break
        except FileNotFoundError:
            pass
    assert v, "REACT_APP_BACKEND_URL not configured"
    return v.rstrip("/")

BASE_URL = _load_backend_url()

CREDS = {
    "superadmin": ("lcorreaq@gmail.com", "IUDigital2026"),
    "direccion":  ("direccion.test@iudigital.edu.co", "Direccion2026!"),
    "decano":     ("decano.test@iudigital.edu.co", "Decano2026!"),
    "coordinador":("coord.test@iudigital.edu.co", "Coord2026!"),
    "profesor":   ("docente.demo@iudigital.edu.co", "Docente2026"),
}


def _login(role: str) -> requests.Session:
    email, password = CREDS[role]
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": email, "password": password},
               timeout=20)
    assert r.status_code == 200, f"login {role}: {r.status_code} {r.text[:200]}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def super_s():
    return _login("superadmin")


@pytest.fixture(scope="module")
def direccion_s():
    return _login("direccion")


@pytest.fixture(scope="module")
def profesor_s():
    return _login("profesor")


# ---------------- Config: overview ----------------

def test_overview_superadmin(super_s):
    r = super_s.get(f"{BASE_URL}/api/config/overview", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ["smtp_enabled", "ai_provider", "ai_enabled",
              "emergent_key_present", "docentes_total", "docentes_credentials_sent"]:
        assert k in data, f"missing {k}"
    assert isinstance(data["docentes_total"], int)


def test_overview_direccion_allowed(direccion_s):
    r = direccion_s.get(f"{BASE_URL}/api/config/overview", timeout=20)
    assert r.status_code == 200


def test_overview_profesor_forbidden(profesor_s):
    r = profesor_s.get(f"{BASE_URL}/api/config/overview", timeout=20)
    assert r.status_code in (401, 403)


# ---------------- Config: SMTP ----------------

def test_smtp_read_superadmin(super_s):
    r = super_s.get(f"{BASE_URL}/api/config/smtp", timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "smtp_host" in d and "smtp_port" in d
    assert "smtp_password_mask" in d


def test_smtp_read_direccion_forbidden(direccion_s):
    r = direccion_s.get(f"{BASE_URL}/api/config/smtp", timeout=20)
    assert r.status_code in (401, 403)


def test_smtp_read_profesor_forbidden(profesor_s):
    r = profesor_s.get(f"{BASE_URL}/api/config/smtp", timeout=20)
    assert r.status_code in (401, 403)


def test_smtp_update_persist_and_empty_password_not_overwrite(super_s):
    # baseline
    r0 = super_s.get(f"{BASE_URL}/api/config/smtp", timeout=20).json()
    prev_pw = r0.get("smtp_password", "")

    # patch host/port/user/from_name; do NOT send password
    payload = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "test-config@iudigital.edu.co",
        "smtp_from_name": "IU Digital Analítica",
        "smtp_enabled": False,
    }
    r = super_s.patch(f"{BASE_URL}/api/config/smtp", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["smtp_host"] == "smtp.gmail.com"
    assert int(d["smtp_port"]) == 587
    assert d["smtp_user"] == payload["smtp_user"]
    assert d["smtp_from_name"] == "IU Digital Analítica"
    assert d["smtp_enabled"] is False

    # empty password field should NOT overwrite existing password
    r2 = super_s.patch(f"{BASE_URL}/api/config/smtp",
                       json={"smtp_password": ""}, timeout=20)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2.get("smtp_password", "") == prev_pw

    # persistence: GET returns saved values
    r3 = super_s.get(f"{BASE_URL}/api/config/smtp", timeout=20).json()
    assert r3["smtp_user"] == payload["smtp_user"]
    assert r3["smtp_from_name"] == "IU Digital Analítica"


def test_smtp_test_returns_400_when_disabled(super_s):
    r = super_s.post(f"{BASE_URL}/api/config/smtp/test",
                     json={"to_email": "nobody@example.com"}, timeout=20)
    assert r.status_code == 400
    body = r.json()
    msg = (body.get("detail") or body.get("message") or "").lower()
    assert "smtp" in msg


# ---------------- Config: AI ----------------

def test_ai_read_and_toggle_provider(super_s):
    r = super_s.get(f"{BASE_URL}/api/config/ai", timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "ai_provider" in d
    assert "emergent_key_present" in d
    assert isinstance(d["emergent_key_present"], bool)

    # switch to gemini_google then back to emergent
    for prov in ("gemini_google", "emergent"):
        rr = super_s.patch(f"{BASE_URL}/api/config/ai",
                           json={"ai_provider": prov}, timeout=20)
        assert rr.status_code == 200, rr.text
        assert rr.json()["ai_provider"] == prov


def test_ai_invalid_provider(super_s):
    r = super_s.patch(f"{BASE_URL}/api/config/ai",
                      json={"ai_provider": "invalid_x"}, timeout=20)
    assert r.status_code == 400


def test_ai_forbidden_for_profesor(profesor_s):
    r = profesor_s.get(f"{BASE_URL}/api/config/ai", timeout=20)
    assert r.status_code in (401, 403)


# ---------------- Send credentials ----------------

def test_send_credentials_one_smtp_disabled(super_s):
    """Uses a disposable test user to avoid clobbering real accounts.
    Endpoint resets password BEFORE checking SMTP => destructive if disabled.
    """
    # Create disposable user
    payload = {
        "email": "TEST_credsend@example.com",
        "full_name": "TEST Credentials Send",
        "role": "profesor",
        "password": "TempTest2026!",
    }
    # Ensure no leftover
    del_r = super_s.get(f"{BASE_URL}/api/admin/users", timeout=20)
    if del_r.status_code == 200:
        users = del_r.json()
        users = users if isinstance(users, list) else users.get("items", [])
        for u in users:
            if u.get("email") == payload["email"]:
                super_s.delete(f"{BASE_URL}/api/admin/users/{u['id']}", timeout=10)
    cr = super_s.post(f"{BASE_URL}/api/admin/users", json=payload, timeout=20)
    if cr.status_code not in (200, 201):
        pytest.skip(f"cannot create disposable user: {cr.status_code} {cr.text[:200]}")
    uid = cr.json().get("id")
    assert uid

    try:
        r2 = super_s.post(f"{BASE_URL}/api/config/send-credentials/{uid}",
                          json={"reset_password": True}, timeout=30)
        assert r2.status_code == 400, r2.text
        msg = (r2.json().get("detail") or "").lower()
        assert "smtp" in msg or "habilit" in msg
    finally:
        super_s.delete(f"{BASE_URL}/api/admin/users/{uid}", timeout=10)


@pytest.mark.skip(reason="Destructive: resets password of ALL profesors before checking SMTP; also >60s → 502. See critical bug report.")
def test_send_credentials_bulk_smtp_disabled(super_s):
    r = super_s.post(f"{BASE_URL}/api/config/send-credentials-bulk",
                     json={"role": "profesor", "only_missing": True},
                     timeout=120)
    assert r.status_code == 200


def test_send_credentials_bulk_forbidden_for_direccion(direccion_s):
    # bulk is superadmin-only per spec
    r = direccion_s.post(f"{BASE_URL}/api/config/send-credentials-bulk",
                        json={"role": "profesor", "only_missing": True}, timeout=20)
    assert r.status_code in (401, 403)


# ---------------- Facultad ficha ----------------

def test_facultad_ficha_structure(super_s):
    # get a facultad id
    r = super_s.get(f"{BASE_URL}/api/admin/facultades", timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    facs = body if isinstance(body, list) else (body.get("items") or body.get("facultades") or [])
    assert facs, "no facultades"
    fid = facs[0].get("id") or facs[0].get("codigo") or facs[0].get("facultad_id")
    assert fid
    r2 = super_s.get(f"{BASE_URL}/api/admin/facultades/{fid}/ficha", timeout=30)
    assert r2.status_code == 200, r2.text
    d = r2.json()
    # sanity: kpis, programas
    keys_lower = {k.lower() for k in d.keys()}
    assert any("kpi" in k or "resumen" in k or "estad" in k for k in keys_lower) or "programas" in keys_lower, f"unexpected shape: {list(d.keys())[:20]}"


def test_facultad_ficha_forbidden_profesor(profesor_s):
    r = profesor_s.get(f"{BASE_URL}/api/admin/facultades", timeout=20)
    # get any fid via superadmin already tested; use dummy id
    r2 = profesor_s.get(f"{BASE_URL}/api/admin/facultades/FCEAC/ficha", timeout=20)
    assert r2.status_code in (401, 403)
