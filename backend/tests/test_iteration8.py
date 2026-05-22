"""
Iteration 8 backend tests:
- Excel templates (estudiantes, notas, docente_materia)
- Bulk uploads (POST /api/uploads/notas, /api/uploads/docente-materia-bulk)
- /api/dashboards/filters now exposes docentes & materias lists
- Dashboards + caracterizacion filters by docente_id/materia_id
- Exports: notas, docente-materia, students with facultad filter
"""
import io
import os
import pytest
import requests
import pandas as pd
import uuid

def _load_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE_URL = _load_url()
EMAIL = "lcorreaq@gmail.com"
PASSWORD = "Chocolate2026!"

XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def real_cedulas(auth):
    # Pull directly from Mongo to avoid relying on a list endpoint
    try:
        from pymongo import MongoClient
        # read MONGO_URL from backend/.env
        url, dbname = None, None
        with open("/app/backend/.env") as f:
            for line in f:
                if line.startswith("MONGO_URL="):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
                if line.startswith("DB_NAME="):
                    dbname = line.split("=", 1)[1].strip().strip('"').strip("'")
        cli = MongoClient(url)
        docs = list(cli[dbname].students.find({}, {"cedula": 1, "_id": 0}).limit(3))
        ceds = [str(d["cedula"]).strip() for d in docs if d.get("cedula")]
    except Exception as e:
        pytest.skip(f"cannot read cedulas from mongo: {e}")
    assert len(ceds) >= 2, f"need real cedulas, got {ceds}"
    return ceds[:3]


# ---------- Templates ----------
@pytest.mark.parametrize("tipo", ["estudiantes", "notas", "docente_materia"])
def test_template_download(auth, tipo):
    r = requests.get(f"{BASE_URL}/api/uploads/template/{tipo}", headers=auth, timeout=30)
    assert r.status_code == 200, f"{tipo}: {r.status_code} {r.text[:200]}"
    assert r.headers.get("content-type", "").startswith(XLSX_CT), r.headers.get("content-type")
    assert len(r.content) > 1000, f"{tipo}: size={len(r.content)}"
    # confirm it is a real xlsx by opening it
    df = pd.read_excel(io.BytesIO(r.content))
    assert len(df.columns) > 0


# ---------- Bulk notas ----------
UNIQ = uuid.uuid4().hex[:6]
TEST_DOC_EMAIL = f"test.docente.{UNIQ}@iudigital.edu.co"
TEST_DOC_NAME = f"Prof Test {UNIQ}"
TEST_MAT_CODE = f"TST-{UNIQ}"
TEST_MAT_NAME = f"Materia Test {UNIQ}"
TEST_PERIODO = "2026-1"


@pytest.fixture(scope="module")
def bulk_notas_result(auth, real_cedulas):
    rows = []
    for ced in real_cedulas:
        rows.append({
            "Cedula": ced, "Periodo": TEST_PERIODO,
            "CodigoMateria": TEST_MAT_CODE, "NombreMateria": TEST_MAT_NAME,
            "NombreDocente": TEST_DOC_NAME, "EmailDocente": TEST_DOC_EMAIL,
            "Nota": 4.2, "Aprobada": "Sí",
        })
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    files = {"file": ("notas_test.xlsx", buf.getvalue(), XLSX_CT)}
    r = requests.post(f"{BASE_URL}/api/uploads/notas", headers=auth, files=files, timeout=60)
    assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
    return r.json()


def test_bulk_notas_response(bulk_notas_result, real_cedulas):
    j = bulk_notas_result
    assert j.get("ok") is True
    assert j.get("inserted") == len(real_cedulas)
    # docente nuevo y materia nueva deben haber sido creados
    assert j.get("docentes_creados", 0) >= 1
    assert j.get("materias_creadas", 0) >= 1


# ---------- Bulk docente-materia ----------
DM_DOC_EMAIL = f"test.dm.{UNIQ}@iudigital.edu.co"
DM_MAT_CODE = f"DM-{UNIQ}"


def test_bulk_docente_materia(auth):
    rows = [{
        "EmailDocente": DM_DOC_EMAIL, "NombreDocente": f"DM Prof {UNIQ}",
        "CodigoMateria": DM_MAT_CODE, "NombreMateria": f"DM Mat {UNIQ}",
        "Periodo": TEST_PERIODO,
    }]
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    files = {"file": ("dm_test.xlsx", buf.getvalue(), XLSX_CT)}
    r = requests.post(f"{BASE_URL}/api/uploads/docente-materia-bulk", headers=auth, files=files, timeout=60)
    assert r.status_code == 200, r.text[:300]
    j = r.json()
    assert j.get("ok") is True
    assert j.get("inserted") == 1
    assert j.get("docentes_creados", 0) >= 1
    assert j.get("materias_creadas", 0) >= 1


# ---------- /api/dashboards/filters ----------
@pytest.fixture(scope="module")
def filters_payload(auth, bulk_notas_result):
    r = requests.get(f"{BASE_URL}/api/dashboards/filters", headers=auth, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def test_filters_has_docentes_and_materias(filters_payload):
    assert "docentes" in filters_payload, list(filters_payload.keys())
    assert "materias" in filters_payload, list(filters_payload.keys())
    assert isinstance(filters_payload["docentes"], list)
    assert isinstance(filters_payload["materias"], list)
    if filters_payload["docentes"]:
        sample = filters_payload["docentes"][0]
        assert "id" in sample and "nombre" in sample
    if filters_payload["materias"]:
        sample = filters_payload["materias"][0]
        assert "id" in sample and "nombre" in sample


def test_filters_includes_new_docente(filters_payload):
    emails_or_names = [d.get("nombre", "").lower() for d in filters_payload["docentes"]]
    found = any(TEST_DOC_EMAIL.lower() in n or TEST_DOC_NAME.lower() in n for n in emails_or_names)
    assert found, f"new docente {TEST_DOC_EMAIL} not in /filters docentes list (got {len(emails_or_names)})"


def _find_docente_id(filters_payload, email_or_name):
    for d in filters_payload["docentes"]:
        n = d.get("nombre", "").lower()
        if email_or_name.lower() in n:
            return d["id"]
    return None


def test_dashboards_executive_filter_by_docente(auth, filters_payload):
    did = _find_docente_id(filters_payload, TEST_DOC_EMAIL) or _find_docente_id(filters_payload, TEST_DOC_NAME)
    assert did, "new docente id not found in filters"
    r = requests.get(f"{BASE_URL}/api/dashboards/executive", params={"docente_id": did}, headers=auth, timeout=30)
    assert r.status_code == 200, r.text[:300]
    j = r.json()
    # Either kpis with total>0 OR empty {}
    kpis = j.get("kpis") or {}
    assert (kpis.get("total", 0) > 0) or (j == {} or kpis == {}), f"unexpected shape: {j}"


def test_caracterizacion_overview_filter_by_docente(auth, filters_payload):
    did = _find_docente_id(filters_payload, TEST_DOC_EMAIL) or _find_docente_id(filters_payload, TEST_DOC_NAME)
    assert did
    r = requests.get(f"{BASE_URL}/api/caracterizacion/overview", params={"docente_id": did}, headers=auth, timeout=60)
    assert r.status_code == 200, r.text[:300]
    # any 200 with json body is acceptable
    assert isinstance(r.json(), dict)


# ---------- Exports ----------
def test_exports_students_with_facultad(auth):
    # Get a facultad name from filters
    r = requests.get(f"{BASE_URL}/api/dashboards/filters", headers=auth, timeout=30)
    facs = r.json().get("facultades") or list((r.json().get("facultad_programa") or {}).keys())
    assert facs, "no facultades found"
    fac = facs[0]
    r = requests.get(f"{BASE_URL}/api/exports/students", params={"fmt": "xlsx", "facultad": fac}, headers=auth, timeout=60)
    assert r.status_code == 200, r.text[:200]
    assert r.headers.get("content-type", "").startswith(XLSX_CT)
    assert len(r.content) > 1000


def test_exports_notas_xlsx(auth):
    r = requests.get(f"{BASE_URL}/api/exports/notas", params={"fmt": "xlsx"}, headers=auth, timeout=60)
    assert r.status_code == 200, r.text[:200]
    assert r.headers.get("content-type", "").startswith(XLSX_CT)
    assert len(r.content) > 500
    df = pd.read_excel(io.BytesIO(r.content))
    assert "cedula" in [c.lower() for c in df.columns] or "info" in [c.lower() for c in df.columns]


def test_exports_docente_materia_xlsx(auth):
    r = requests.get(f"{BASE_URL}/api/exports/docente-materia", params={"fmt": "xlsx"}, headers=auth, timeout=60)
    assert r.status_code == 200, r.text[:200]
    assert r.headers.get("content-type", "").startswith(XLSX_CT)
    df = pd.read_excel(io.BytesIO(r.content))
    cols = set(df.columns)
    expected = {"EmailDocente", "NombreDocente", "CodigoMateria", "NombreMateria", "Periodo"}
    # tolerant: at least 3 expected cols present OR info row
    assert expected.issubset(cols) or "info" in cols, f"missing cols: {expected - cols}"
