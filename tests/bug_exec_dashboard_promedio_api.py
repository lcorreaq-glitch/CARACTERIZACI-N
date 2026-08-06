#!/usr/bin/env python3
"""Focused regression test for executive dashboard weighted promedio KPI."""
import json
import math
import os
import sys
from pathlib import Path

import requests


def load_frontend_backend_url() -> str:
    env_path = Path("/app/frontend/.env")
    for line in env_path.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


def assert_equal(actual, expected, name):
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")


def main():
    base = load_frontend_backend_url().rstrip("/")
    api = f"{base}/api"
    session = requests.Session()

    login_resp = session.post(
        f"{api}/auth/login",
        json={"email": "lcorreaq@gmail.com", "password": "IUDigital2026"},
        timeout=30,
    )
    print(f"Login status: {login_resp.status_code}")
    login_resp.raise_for_status()
    token = login_resp.json()["access_token"]

    dash_resp = session.get(
        f"{api}/dashboards/executive",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    print(f"Dashboard status: {dash_resp.status_code}")
    dash_resp.raise_for_status()
    payload = dash_resp.json()
    kpis = payload.get("kpis", {})
    print("KPI payload:")
    print(json.dumps(kpis, indent=2, ensure_ascii=False, sort_keys=True))

    # Original bug: general average showed 3.80 and did not match period averages.
    promedio = kpis.get("promedio")
    if not (3.28 <= promedio <= 3.30):
        raise AssertionError(f"kpis.promedio should be weighted promedio around 3.29, got {promedio}")
    if math.isclose(promedio, 3.80, abs_tol=0.005):
        raise AssertionError("kpis.promedio still shows incorrect 3.80")

    expected_kpis = {
        "total": 16461,
        "matriculados": 14244,
        "programas": 21,
        "facultades": 5,
        "rurales": 3404,
        "victimas": 4852,
        "discapacidad": 202,
        "notas_2025_2": 84871,
        "notas_2026_1": 84505,
    }
    for key, expected in expected_kpis.items():
        assert_equal(kpis.get(key), expected, key)

    period_2025 = kpis.get("promedio_2025_2")
    period_2026 = kpis.get("promedio_2026_1")
    if not math.isclose(period_2025, 3.45, abs_tol=0.005):
        raise AssertionError(f"promedio_2025_2 expected 3.45, got {period_2025}")
    if not math.isclose(period_2026, 3.12, abs_tol=0.005):
        raise AssertionError(f"promedio_2026_1 expected 3.12, got {period_2026}")

    weighted = ((84871 * 3.45) + (84505 * 3.12)) / 169376
    print(f"Weighted formula result from rounded period averages: {weighted:.6f}")
    if not math.isclose(round(weighted, 2), promedio, abs_tol=0.01):
        raise AssertionError(f"weighted formula rounded should match promedio; formula={weighted}, promedio={promedio}")

    required_arrays = ["by_edad", "by_vulnerabilidad", "by_departamento", "by_ubicacion"]
    for key in required_arrays:
        if not isinstance(payload.get(key), list) or len(payload[key]) == 0:
            raise AssertionError(f"{key} should be a non-empty list for dashboard chart data")
        print(f"{key}: {len(payload[key])} rows")

    print("API regression passed: executive promedio is weighted and coherent.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"API regression failed: {exc}", file=sys.stderr)
        sys.exit(1)