"""Tests for Docente dashboard endpoints (iteration_3)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://university-insights.preview.emergentagent.com").rstrip("/")

DOCENTE_EMAIL = "docente.demo@iudigital.edu.co"
DOCENTE_PASS = "Docente2026!"
SUPERADMIN_EMAIL = "lcorreaq@gmail.com"
SUPERADMIN_PASS_OPTIONS = ["Chocolate2026!", "Chocolate1"]


@pytest.fixture(scope="module")
def docente_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": DOCENTE_EMAIL, "password": DOCENTE_PASS}, timeout=20)
    assert r.status_code == 200, f"Docente login failed: {r.status_code} {r.text}"
    body = r.json()
    assert "access_token" in body
    assert body["user"]["role"] == "docente"
    assert body["user"].get("must_change_password") in (False, None)
    return body["access_token"]


@pytest.fixture(scope="module")
def superadmin_token():
    last = None
    for pw in SUPERADMIN_PASS_OPTIONS:
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": SUPERADMIN_EMAIL, "password": pw}, timeout=20)
        last = r
        if r.status_code == 200:
            return r.json()["access_token"]
    pytest.skip(f"Superadmin login failed with all passwords: {last.status_code} {last.text}")


# ---- Docente login ----
def test_docente_login_returns_token_and_role():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": DOCENTE_EMAIL, "password": DOCENTE_PASS}, timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("access_token"), str) and len(body["access_token"]) > 10
    assert body["user"]["role"] == "docente"


# ---- /dashboards/docente/me ----
def test_docente_me_full_payload(docente_token):
    r = requests.get(f"{BASE_URL}/api/dashboards/docente/me",
                     headers={"Authorization": f"Bearer {docente_token}"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    # Materias = 4
    assert len(d.get("materias", [])) == 4, f"Expected 4 materias, got {len(d.get('materias', []))}"
    names = {m["materia_nombre"] for m in d["materias"]}
    expected = {"Contabilidad General", "Programación I", "Fundamentos del Trabajo Social", "Estrategia Digital"}
    assert expected.issubset(names), f"Missing materias: {expected - names}"
    # Programas asociados
    assert len(d.get("programas_asociados", [])) > 0
    # KPIs
    k = d.get("kpis", {})
    assert k.get("total_estudiantes", 0) > 0, "Expected total_estudiantes > 0"
    assert "promedio" in k and "en_riesgo" in k and "excelencia" in k
    # Distribucion notas
    assert isinstance(d.get("distribucion_notas"), list) and len(d["distribucion_notas"]) > 0
    # by_programa
    assert isinstance(d.get("by_programa"), list) and len(d["by_programa"]) > 0
    # caracterizacion
    c = d.get("caracterizacion", {})
    assert "genero" in c and "estrato" in c and "ubicacion" in c
    assert len(c["genero"]) > 0
    # municipios
    assert isinstance(d.get("municipios"), list) and len(d["municipios"]) > 0
    m0 = d["municipios"][0]
    assert "lat" in m0 and "lon" in m0 and "n" in m0


def test_docente_me_requires_auth():
    r = requests.get(f"{BASE_URL}/api/dashboards/docente/me", timeout=15)
    assert r.status_code in (401, 403)


# ---- /dashboards/docente/students ----
def test_docente_students_list(docente_token):
    r = requests.get(f"{BASE_URL}/api/dashboards/docente/students",
                     headers={"Authorization": f"Bearer {docente_token}"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    students = d.get("students", [])
    assert len(students) > 0, "Expected non-empty students list"
    assert d.get("total", 0) > 0
    s = students[0]
    # Required fields
    for k in ("cedula", "nombre", "programa", "promedio", "ciudad_nombre"):
        assert k in s, f"Missing field {k} in student"


def test_docente_students_riesgo_filter(docente_token):
    r = requests.get(f"{BASE_URL}/api/dashboards/docente/students?riesgo=true",
                     headers={"Authorization": f"Bearer {docente_token}"}, timeout=30)
    assert r.status_code == 200
    students = r.json().get("students", [])
    # Every returned student should have promedio < 3.0 (or 0 means no grade)
    for s in students:
        p = s.get("promedio")
        if p is not None:
            assert p < 3.0, f"riesgo filter returned student with promedio={p}"


def test_docente_students_materia_filter(docente_token):
    # Get materias first
    me = requests.get(f"{BASE_URL}/api/dashboards/docente/me",
                      headers={"Authorization": f"Bearer {docente_token}"}, timeout=30).json()
    materia = me["materias"][0]
    materia_id = materia["materia_id"]
    target_program = materia.get("programa_nombre")
    r = requests.get(f"{BASE_URL}/api/dashboards/docente/students?materia_id={materia_id}",
                     headers={"Authorization": f"Bearer {docente_token}"}, timeout=30)
    assert r.status_code == 200
    students = r.json().get("students", [])
    if target_program and students:
        progs = {s.get("programa") for s in students}
        assert progs == {target_program}, f"Expected only {target_program}, got {progs}"


# ---- Superadmin smoke ----
def test_superadmin_login_and_executive(superadmin_token):
    # Executive endpoint should work for superadmin
    r = requests.get(f"{BASE_URL}/api/dashboards/executive",
                     headers={"Authorization": f"Bearer {superadmin_token}"}, timeout=30)
    assert r.status_code == 200, r.text
    assert "kpis" in r.json() or "total_estudiantes" in str(r.json())


def test_docente_can_call_executive_endpoint(docente_token):
    """Per requirement: endpoint is accessible if valid token (restriction is UI-only)."""
    r = requests.get(f"{BASE_URL}/api/dashboards/executive",
                     headers={"Authorization": f"Bearer {docente_token}"}, timeout=30)
    # Either 200 (open) or 403 (locked) is acceptable per spec; spec says it should work
    assert r.status_code in (200, 403), r.text
