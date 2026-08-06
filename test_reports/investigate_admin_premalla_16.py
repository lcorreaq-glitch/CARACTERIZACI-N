#!/usr/bin/env python3
"""Extract API evidence for the non-academic admin group still receiving averages."""
import json
import os
import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8001")
EMAIL = os.environ.get("TEST_EMAIL", "lcorreaq@gmail.com")
PASSWORD = os.environ.get("TEST_PASSWORD", "IUDigital2026")
CODIGO = "PRECBH2602000_20003"

s = requests.Session()
login = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
login.raise_for_status()
s.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})

list_resp = s.get(f"{BASE_URL}/api/admin/grupos?codigo_grupo={CODIGO}", timeout=60)
detail_resp = s.get(f"{BASE_URL}/api/admin/grupos/{CODIGO}", timeout=60)
list_body = list_resp.json()
detail_body = detail_resp.json()

print(json.dumps({
    "list_status": list_resp.status_code,
    "list_items": list_body.get("items", []),
    "detail_status": detail_resp.status_code,
    "detail_grupo": detail_body.get("grupo"),
    "detail_total_estudiantes": detail_body.get("total_estudiantes"),
    "detail_notas_por_periodo": detail_body.get("notas_por_periodo"),
}, ensure_ascii=False, indent=2, default=str))