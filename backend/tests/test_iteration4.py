"""Iteration 4 backend tests: divipola admin, exports, historical 2026-1, facultades."""
import os
import io
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://university-insights.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPERADMIN_EMAIL = "lcorreaq@gmail.com"
SUPERADMIN_PASS = "Chocolate2026!"
FALLBACK_PASS = "Chocolate1"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASS})
    if r.status_code != 200:
        r = requests.post(f"{API}/auth/login", json={"email": SUPERADMIN_EMAIL, "password": FALLBACK_PASS})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# --- DIVIPOLA Admin ---
class TestDivipolaAdmin:
    def test_list_municipios(self, auth_headers):
        r = requests.get(f"{API}/admin/divipola", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        # could be either {"municipios":[...]} or list
        items = data.get("municipios") if isinstance(data, dict) else data
        assert isinstance(items, list)
        assert len(items) >= 200, f"Expected >=200 municipios, got {len(items)}"
        keys = {"codigo", "nombre", "departamento", "pais", "lat", "lon"}
        for k in keys:
            assert k in items[0], f"Missing key {k} in {items[0]}"

    def test_paises(self, auth_headers):
        r = requests.get(f"{API}/admin/divipola/paises", headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        paises = data.get("paises") if isinstance(data, dict) else data
        assert isinstance(paises, list)
        assert len(paises) >= 10, f"Expected >=10 paises, got {len(paises)}"
        names_upper = [str(p).upper() if isinstance(p, str) else str(p.get("nombre", p.get("pais", ""))).upper() for p in paises]
        # USA may be represented as "ESTADOS UNIDOS" in backend
        usa_present = any("USA" in n or "ESTADOS UNIDOS" in n for n in names_upper)
        assert usa_present, f"Missing USA/Estados Unidos in {names_upper}"
        for required in ["COLOMBIA", "VENEZUELA", "ECUADOR", "PANAMA", "ESPA"]:
            assert any(required in n for n in names_upper), f"Missing pais containing {required} in {names_upper}"

    def test_create_municipio(self, auth_headers):
        code = f"TST{uuid.uuid4().hex[:5].upper()}"
        payload = {
            "codigo": code,
            "nombre": f"TEST_MUNI_{code}",
            "departamento": "TEST_DEPT",
            "pais": "COLOMBIA",
            "lat": 4.5,
            "lon": -74.1,
        }
        r = requests.post(f"{API}/admin/divipola", headers=auth_headers, json=payload)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body.get("codigo") == code or body.get("nombre", "").startswith("TEST_MUNI")
        # Cleanup if delete supported
        muni_id = body.get("id") or body.get("_id") or code
        try:
            requests.delete(f"{API}/admin/divipola/{muni_id}", headers=auth_headers)
        except Exception:
            pass


# --- Exports ---
class TestExports:
    def _check_xlsx(self, r, min_size=100_000):
        assert r.status_code == 200, r.text[:300]
        ct = r.headers.get("content-type", "")
        assert "spreadsheet" in ct or "xlsx" in ct or "octet-stream" in ct, f"Unexpected content-type: {ct}"
        size = len(r.content)
        assert size >= min_size, f"File too small: {size} bytes (expected >= {min_size})"
        # xlsx is a zip, must start with PK
        assert r.content[:2] == b"PK", "Not a valid xlsx (PK header missing)"

    def test_export_students_xlsx(self, auth_headers):
        r = requests.get(f"{API}/exports/students", headers=auth_headers, params={"fmt": "xlsx"}, timeout=120)
        self._check_xlsx(r, min_size=100_000)

    def test_export_dashboard_ejecutivo(self, auth_headers):
        r = requests.get(f"{API}/exports/dashboard/ejecutivo", headers=auth_headers, params={"fmt": "xlsx"}, timeout=120)
        self._check_xlsx(r, min_size=3_000)

    def test_export_dashboard_caracterizacion(self, auth_headers):
        r = requests.get(f"{API}/exports/dashboard/caracterizacion", headers=auth_headers, params={"fmt": "xlsx"}, timeout=120)
        self._check_xlsx(r, min_size=3_000)

    def test_export_dashboard_territorial(self, auth_headers):
        r = requests.get(f"{API}/exports/dashboard/territorial", headers=auth_headers, params={"fmt": "xlsx"}, timeout=120)
        self._check_xlsx(r, min_size=3_000)

    def test_export_divipola(self, auth_headers):
        r = requests.get(f"{API}/exports/divipola", headers=auth_headers, params={"fmt": "xlsx"}, timeout=120)
        self._check_xlsx(r, min_size=3_000)


# --- Historical 2026-1 ---
class TestHistorical:
    def test_includes_2026_1(self, auth_headers):
        r = requests.get(f"{API}/dashboards/historical", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        series = data.get("series_periodo", [])
        periodos = [str(s.get("periodo") or s.get("name") or s.get("label")) for s in series]
        assert any("2026-1" in p for p in periodos), f"2026-1 missing in periodos: {periodos}"


# --- Facultades (6 expected) ---
class TestFacultades:
    EXPECTED = [
        "Ciencias Administrativas y Econ",  # Económicas (allow accent diff)
        "Ciencias Ambientales",
        "Ciencias y Tecnolog",  # Tecnologías Digitales
        "Ingenier",  # Ingeniería
        "Educaci",  # Educación
        "Ciencias Sociales y Human",
    ]

    def test_six_facultades(self, auth_headers):
        r = requests.get(f"{API}/admin/facultades", headers=auth_headers)
        assert r.status_code == 200, r.text
        facs = r.json()
        names = [f.get("nombre", "") for f in facs]
        assert len(facs) >= 6, f"Expected >=6 facultades, got {len(facs)}: {names}"
        for needle in self.EXPECTED:
            assert any(needle.lower() in n.lower() for n in names), f"Missing facultad matching '{needle}' in {names}"
