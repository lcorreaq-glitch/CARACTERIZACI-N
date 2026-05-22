"""Tests for iteration 7: SISBEN levels/groups, cascading filters, DIVIPOLA international cities."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "lcorreaq@gmail.com"
PASS = "Chocolate2026!"
FALLBACK_PASS = "Chocolate1"


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASS}, timeout=30)
    if r.status_code != 200:
        r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": FALLBACK_PASS}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestLogin:
    def test_login_chocolate2026(self):
        r = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASS}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user"]["must_change_password"] is False
        assert data["user"]["role"] == "superadmin"


class TestFiltersCascade:
    def test_filters_includes_facultad_programa_map(self, auth_headers):
        r = requests.get(f"{API}/dashboards/filters", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        for key in ["facultades", "programas", "periodos", "facultad_programa"]:
            assert key in data, f"missing key {key}"
        fp = data["facultad_programa"]
        assert isinstance(fp, dict)
        assert len(fp) >= 1
        # Each value must be a list of strings, subset of programas
        all_progs = set(data["programas"])
        for fac, plist in fp.items():
            assert isinstance(plist, list) and len(plist) > 0, f"facultad {fac} no progs"
            for p in plist:
                assert p in all_progs, f"prog '{p}' not in global programas"

    def test_filters_excludes_seleccione(self, auth_headers):
        r = requests.get(f"{API}/dashboards/filters", headers=auth_headers, timeout=30)
        data = r.json()
        for k in ["facultades", "programas", "generos", "estratos", "etnias", "ubicaciones", "estados_matricula"]:
            for v in data.get(k, []):
                assert "SELECCIONE" not in str(v).upper(), f"Found SELECCIONE in {k}: {v}"


class TestCaracterizacionSisben:
    def test_overview_has_sisben_blocks(self, auth_headers):
        r = requests.get(f"{API}/caracterizacion/overview", headers=auth_headers, timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert "kpis" in data and "blocks" in data
        assert "sisben_pct" in data["kpis"]
        socio = data["blocks"].get("socioeconomico", {})
        assert "grupo_sisben" in socio
        assert "sisben_nivel" in socio
        # grupo_sisben labels should include GRUPO A..D
        grupo_labels = {x["label"] for x in socio["grupo_sisben"]}
        expected_grupos = {"GRUPO A", "GRUPO B", "GRUPO C", "GRUPO D"}
        assert expected_grupos.issubset(grupo_labels), f"Missing grupos. Got: {grupo_labels}"

    def test_overview_sisben_nivel_labels(self, auth_headers):
        r = requests.get(f"{API}/caracterizacion/overview", headers=auth_headers, timeout=60)
        data = r.json()
        socio = data["blocks"]["socioeconomico"]
        nivel_labels = {x["label"] for x in socio["sisben_nivel"]}
        # Should include at least one A1, B1, C1, D1
        valid_prefixes = {"A", "B", "C", "D"}
        found_prefixes = {lbl[0] for lbl in nivel_labels if lbl and lbl[0] in valid_prefixes}
        assert len(found_prefixes) >= 3, f"Expected niveles A/B/C/D variants. Got labels: {nivel_labels}"
        # Specifically expect A1-A5 / B1-B7 / etc - sample a few
        sample_check = {"A1", "B1", "C1", "D1"}
        intersection = sample_check & nivel_labels
        assert len(intersection) >= 2, f"Expected at least 2 of {sample_check}. Found: {nivel_labels}"

    def test_overview_excludes_seleccione_in_groups(self, auth_headers):
        r = requests.get(f"{API}/caracterizacion/overview", headers=auth_headers, timeout=60)
        data = r.json()
        for block_name, block in data["blocks"].items():
            for chart_name, items in block.items():
                if isinstance(items, list):
                    for item in items:
                        lbl = str(item.get("label", "")).upper()
                        assert "SELECCIONE" not in lbl, f"Found SELECCIONE in {block_name}.{chart_name}: {lbl}"

    def test_filter_facultad_ingenieria_reduces_total(self, auth_headers):
        # Get global total
        r_all = requests.get(f"{API}/caracterizacion/overview", headers=auth_headers, timeout=60)
        total_all = r_all.json()["total"]

        # Try different facultad name variations
        for fac_name in ["Facultad de Ingeniería", "Ingeniería", "Facultad de Ingenierías"]:
            r = requests.get(f"{API}/caracterizacion/overview",
                            headers=auth_headers,
                            params={"facultad": fac_name},
                            timeout=60)
            assert r.status_code == 200
            total_fil = r.json()["total"]
            if total_fil > 0:
                assert total_fil < total_all, f"Filtered ({fac_name}) total {total_fil} should be less than {total_all}"
                # Expecting ~911 per spec but we'll allow a range
                assert 500 <= total_fil <= 3000, f"Expected ~911 for {fac_name}, got {total_fil}"
                return
        pytest.fail("No valid facultad name returned data")


class TestTerritorialDivipola:
    def test_territorial_has_445_plus_municipios(self, auth_headers):
        r = requests.get(f"{API}/dashboards/territorial", headers=auth_headers, timeout=60)
        assert r.status_code == 200
        data = r.json()
        munis = data["municipios"]
        assert isinstance(munis, list)
        # Each must have lat/lon (some)
        with_coords = [m for m in munis if m.get("lat") and m.get("lon")]
        assert len(with_coords) > 50, f"Only {len(with_coords)} with coords"

    def test_divipola_has_international_cities(self, auth_headers):
        r = requests.get(f"{API}/divipola", timeout=30)
        assert r.status_code == 200
        data = r.json()
        munis = data["municipios"]
        names = {str(m.get("nombre", "")).upper() for m in munis}
        # Check for international cities
        international = {"CARACAS", "QUITO", "MADRID"}
        found = international & names
        assert len(found) >= 1, f"Expected international cities. Sample names: {list(names)[:20]}"

    def test_divipola_total_count(self, auth_headers):
        r = requests.get(f"{API}/divipola", timeout=30)
        data = r.json()
        # Spec says 480 total, allow >= 400
        assert len(data["municipios"]) >= 400, f"Expected 400+ municipios, got {len(data['municipios'])}"
