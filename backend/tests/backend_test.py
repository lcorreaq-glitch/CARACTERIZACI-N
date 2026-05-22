"""Backend integration tests for IU Digital Analytics."""
import os
import io
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or "https://university-insights.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

SUPERADMIN_EMAIL = "lcorreaq@gmail.com"
SUPERADMIN_PASS = "Chocolate2026!"
FALLBACK_PASS = "Chocolate1"


# --- Fixtures ---
@pytest.fixture(scope="session")
def token():
    """Get superadmin token. Try main password, then fallback (must_change flow)."""
    r = requests.post(f"{API}/auth/login", json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASS})
    if r.status_code != 200:
        r = requests.post(f"{API}/auth/login", json={"email": SUPERADMIN_EMAIL, "password": FALLBACK_PASS})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# --- Health ---
class TestHealth:
    def test_root(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "IU Digital" in data["app"]


# --- Auth ---
class TestAuth:
    def test_login_success(self):
        r = requests.post(f"{API}/auth/login", json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASS})
        if r.status_code != 200:
            # try fallback
            r = requests.post(f"{API}/auth/login", json={"email": SUPERADMIN_EMAIL, "password": FALLBACK_PASS})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == SUPERADMIN_EMAIL
        assert data["user"]["role"] == "superadmin"
        # Per request: must_change_password should be false
        assert data["user"]["must_change_password"] is False, "Expected must_change_password=False after initial reset"

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": SUPERADMIN_EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_me(self, auth_headers):
        r = requests.get(f"{API}/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == SUPERADMIN_EMAIL
        assert data["role"] == "superadmin"

    def test_me_unauth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code in (401, 403)


# --- Dashboards ---
class TestDashboards:
    def test_executive_kpis(self, auth_headers):
        # Wait briefly in case seed still ongoing
        for _ in range(6):
            r = requests.get(f"{API}/dashboards/executive", headers=auth_headers)
            assert r.status_code == 200
            data = r.json()
            kpis = data.get("kpis", {})
            if kpis.get("total", 0) >= 12000:
                break
            time.sleep(5)
        kpis = data["kpis"]
        assert kpis["total"] >= 12000, f"Total students {kpis.get('total')} < 12000"
        assert "matriculados" in kpis
        assert kpis["programas"] >= 1
        assert kpis["facultades"] >= 1
        assert isinstance(data["by_program"], list) and len(data["by_program"]) > 0
        assert isinstance(data["by_genero"], list)
        assert isinstance(data["by_estrato"], list)
        assert isinstance(data["by_ubicacion"], list)

    def test_executive_filter_facultad(self, auth_headers):
        r_all = requests.get(f"{API}/dashboards/executive", headers=auth_headers)
        total_all = r_all.json()["kpis"]["total"]
        r = requests.get(f"{API}/dashboards/executive", headers=auth_headers, params={"facultad": "Facultad de Ingenierías"})
        assert r.status_code == 200
        data = r.json()
        total_fil = data["kpis"].get("total", 0)
        # filter must reduce total (or be equal only if there's only this facultad)
        assert total_fil <= total_all
        assert total_fil > 0, "Filtered total should be > 0 for valid facultad"

    def test_academic(self, auth_headers):
        r = requests.get(f"{API}/dashboards/academic", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        for key in ["by_program_avg", "by_facultad", "distribucion_notas", "en_riesgo", "excelencia", "avance"]:
            assert key in data, f"Missing key {key}"
        assert isinstance(data["by_program_avg"], list)
        assert isinstance(data["en_riesgo"], int)
        assert isinstance(data["excelencia"], int)

    def test_territorial(self, auth_headers):
        r = requests.get(f"{API}/dashboards/territorial", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "municipios" in data and "por_departamento" in data
        munis = data["municipios"]
        assert isinstance(munis, list) and len(munis) > 0
        # validate lat/lon
        valid = [m for m in munis if isinstance(m.get("lat"), (int, float)) and isinstance(m.get("lon"), (int, float))]
        assert len(valid) > 0, "Expected at least some municipios with lat/lon"

    def test_historical(self, auth_headers):
        r = requests.get(f"{API}/dashboards/historical", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "series_periodo" in data and "by_program" in data
        assert isinstance(data["series_periodo"], list)

    def test_filters(self, auth_headers):
        r = requests.get(f"{API}/dashboards/filters", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        for k in ["programas", "facultades", "periodos", "generos", "estratos", "etnias", "ubicaciones", "estados_matricula"]:
            assert k in data
        assert len(data["programas"]) > 0
        assert len(data["facultades"]) > 0


# --- Divipola ---
class TestDivipola:
    def test_municipios(self, auth_headers):
        r = requests.get(f"{API}/divipola")
        assert r.status_code == 200
        data = r.json()
        assert "municipios" in data
        assert len(data["municipios"]) >= 100


# --- Admin CRUD ---
class TestAdmin:
    def test_list_users(self, auth_headers):
        r = requests.get(f"{API}/admin/users", headers=auth_headers)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        emails = [u["email"] for u in users]
        assert SUPERADMIN_EMAIL in emails

    def test_create_docente_user_and_cleanup(self, auth_headers):
        email = f"test_docente_{uuid.uuid4().hex[:8]}@test.io"
        payload = {
            "email": email,
            "password": "TestPass123!",
            "full_name": "TEST Docente",
            "role": "docente",
        }
        r = requests.post(f"{API}/admin/users", headers=auth_headers, json=payload)
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["email"] == email
        assert created["role"] == "docente"
        assert created["must_change_password"] is True
        user_id = created["id"]

        # verify list contains it
        r2 = requests.get(f"{API}/admin/users", headers=auth_headers)
        emails = [u["email"] for u in r2.json()]
        assert email in emails

        # cleanup
        rd = requests.delete(f"{API}/admin/users/{user_id}", headers=auth_headers)
        assert rd.status_code == 200

    @pytest.mark.parametrize("name,collection", [
        ("facultades", "facultades"),
        ("programas", "programas"),
        ("materias", "materias"),
        ("periodos", "periodos"),
    ])
    def test_catalog_list(self, auth_headers, name, collection):
        r = requests.get(f"{API}/admin/{name}", headers=auth_headers)
        assert r.status_code == 200, f"GET /api/admin/{name}: {r.text}"
        assert isinstance(r.json(), list)

    def test_catalog_create_and_delete(self, auth_headers):
        # facultad
        payload = {"nombre": f"TEST_FAC_{uuid.uuid4().hex[:6]}", "codigo": "TST"}
        r = requests.post(f"{API}/admin/facultades", headers=auth_headers, json=payload)
        assert r.status_code == 200, r.text
        item = r.json()
        assert item["nombre"] == payload["nombre"]
        fac_id = item["id"]
        rd = requests.delete(f"{API}/admin/facultades/{fac_id}", headers=auth_headers)
        assert rd.status_code == 200

    def test_docente_materia_create(self, auth_headers):
        # Create temp docente
        email = f"test_dm_{uuid.uuid4().hex[:8]}@test.io"
        ru = requests.post(f"{API}/admin/users", headers=auth_headers, json={
            "email": email, "password": "Pass1234!", "full_name": "TEST DM", "role": "docente"
        })
        assert ru.status_code == 200
        docente_id = ru.json()["id"]

        # Create temp materia
        rm = requests.post(f"{API}/admin/materias", headers=auth_headers, json={
            "nombre": f"TEST_MAT_{uuid.uuid4().hex[:6]}", "codigo": "MAT01"
        })
        assert rm.status_code == 200
        materia_id = rm.json()["id"]

        # Create relation
        rdm = requests.post(f"{API}/admin/docente-materia", headers=auth_headers, json={
            "docente_id": docente_id, "materia_id": materia_id, "periodo": "2025-1"
        })
        assert rdm.status_code == 200, rdm.text
        dm_id = rdm.json()["id"]

        # list
        rl = requests.get(f"{API}/admin/docente-materia", headers=auth_headers)
        assert rl.status_code == 200
        assert any(x["id"] == dm_id for x in rl.json())

        # cleanup
        requests.delete(f"{API}/admin/docente-materia/{dm_id}", headers=auth_headers)
        requests.delete(f"{API}/admin/users/{docente_id}", headers=auth_headers)
        requests.delete(f"{API}/admin/materias/{materia_id}", headers=auth_headers)


# --- Uploads ---
class TestUploads:
    def test_list_uploads(self, auth_headers):
        r = requests.get(f"{API}/uploads/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_preview_excel(self, auth_headers):
        xlsx_path = "/app/data/caracterizacion.xlsx"
        if not os.path.exists(xlsx_path):
            pytest.skip("Excel file not present")
        with open(xlsx_path, "rb") as f:
            files = {"file": ("caracterizacion.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            r = requests.post(f"{API}/uploads/preview", headers=auth_headers, files=files, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total_rows"] > 0
        assert isinstance(data["columns"], list)
        assert isinstance(data["preview"], list)


# --- AI Insights ---
class TestAI:
    def test_insights_ejecutivo(self, auth_headers):
        r = requests.post(f"{API}/ai/insights", headers=auth_headers,
                          json={"scope": "ejecutivo"}, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["scope"] == "ejecutivo"
        assert data["insight"] and len(data["insight"]) > 20
