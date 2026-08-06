#!/usr/bin/env python3
"""Focused negative checks for dashboard endpoints not covered by the main happy-path script."""
import json
import re
from datetime import datetime
from pathlib import Path

import requests
from pymongo import MongoClient

APP = Path("/app")
OUT = APP / "test_reports" / "academic_filter_gap_evidence.json"


def read_env(path):
    vals = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        vals[k] = v.strip().strip('"').strip("'")
    return vals


BASE = read_env(APP / "frontend" / ".env")["REACT_APP_BACKEND_URL"].rstrip("/")
BACK_ENV = read_env(APP / "backend" / ".env")
DB_NAME = BACK_ENV.get("DB_NAME", "iudigital")
MONGO_URL = BACK_ENV.get("MONGO_URL", "mongodb://localhost:27017")
NON_ACADEMIC_RE = r"(extensi[oó]n\s+acad[eé]mica|^curso\s|diplomad|fuera\s+de\s+la\s+malla|-\s+extens)"
RX = re.compile(NON_ACADEMIC_RE, re.I)
ACADEMIC_MATCH = {
    "$and": [
        {"codigo_asignatura": {"$not": {"$regex": r"^EXT", "$options": "i"}}},
        {"$or": [
            {"programa": {"$exists": False}},
            {"programa": None},
            {"programa": ""},
            {"programa": {"$not": {"$regex": NON_ACADEMIC_RE, "$options": "i"}}},
        ]},
    ]
}


def api_get(path, token, **params):
    r = requests.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"}, params=params, timeout=60)
    return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text


def round2(v):
    return round(float(v or 0), 2)


def is_nonacademic(note):
    return (note.get("codigo_asignatura") or "").upper().startswith("EXT") or bool(RX.search(note.get("programa") or ""))


def main():
    evidence = {"timestamp": datetime.utcnow().isoformat() + "Z", "checks": {}, "failures": []}
    login = requests.post(f"{BASE}/api/auth/login", json={"email": "lcorreaq@gmail.com", "password": "IUDigital2026"}, timeout=30)
    evidence["checks"]["login_status"] = login.status_code
    login.raise_for_status()
    token = login.json()["access_token"]
    db = MongoClient(MONGO_URL)[DB_NAME]

    # /dashboards/historical is a real frontend dashboard endpoint (frontend/src/pages/Historical.jsx).
    raw_period_rows = list(db.historico_notas.aggregate([
        {"$group": {"_id": "$periodo", "avg": {"$avg": "$nota"}, "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]))
    academic_period_rows = list(db.historico_notas.aggregate([
        {"$match": ACADEMIC_MATCH},
        {"$group": {"_id": "$periodo", "avg": {"$avg": "$nota"}, "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]))
    raw_periods = {r["_id"]: {"n": r["n"], "promedio": round2(r["avg"])} for r in raw_period_rows}
    academic_periods = {r["_id"]: {"n": r["n"], "promedio": round2(r["avg"])} for r in academic_period_rows}
    status, hist = api_get("/api/dashboards/historical", token)
    evidence["checks"]["historical_status"] = status
    if status == 200:
        api_periods = {r["periodo"]: {"n": r["n_notas"], "promedio": r["promedio"]} for r in hist.get("series_periodo", [])}
        evidence["checks"]["historical_api_periods"] = api_periods
        evidence["checks"]["historical_expected_academic_periods"] = academic_periods
        evidence["checks"]["historical_raw_periods"] = raw_periods
        for p, expected in academic_periods.items():
            if api_periods.get(p) != expected:
                evidence["failures"].append(f"/dashboards/historical period {p} returned {api_periods.get(p)}; expected academic-only {expected}")
    else:
        evidence["failures"].append(f"/dashboards/historical returned status {status}")

    # Docente Mi Panel opens a student's historical notes via this endpoint.
    nonacademic_match = {"$or": [
        {"codigo_asignatura": {"$regex": r"^EXT", "$options": "i"}},
        {"programa": {"$regex": NON_ACADEMIC_RE, "$options": "i"}},
    ]}
    cedula = None
    sample_note = None
    for note in db.historico_notas.find(nonacademic_match, {"_id": 0, "cedula": 1, "codigo_asignatura": 1, "programa": 1, "asignatura_nombre": 1, "nota": 1}).limit(20000):
        if db.students.find_one({"cedula": note.get("cedula")}, {"_id": 1}):
            cedula = note.get("cedula")
            sample_note = note
            break
    evidence["checks"]["sample_student_with_nonacademic_note"] = {"cedula": cedula, "sample_note": sample_note}
    if cedula:
        status, payload = api_get(f"/api/dashboards/docente/estudiante/{cedula}/historico", token)
        evidence["checks"]["docente_student_historico_status"] = status
        if status == 200:
            returned_nonacademic = []
            for period in payload.get("periodos", []):
                for note in period.get("notas", []):
                    if is_nonacademic(note):
                        returned_nonacademic.append({
                            "periodo": period.get("periodo"),
                            "codigo_asignatura": note.get("codigo_asignatura"),
                            "programa": note.get("programa"),
                            "asignatura_nombre": note.get("asignatura_nombre"),
                            "nota": note.get("nota"),
                        })
                        if len(returned_nonacademic) >= 10:
                            break
                if len(returned_nonacademic) >= 10:
                    break
            evidence["checks"]["docente_student_historico_returned_nonacademic_sample"] = returned_nonacademic
            if returned_nonacademic:
                evidence["failures"].append("/dashboards/docente/estudiante/{cedula}/historico still returns EXT/extension/fuera-de-malla notes")
        else:
            evidence["failures"].append(f"docente student historico returned status {status}")
    else:
        evidence["failures"].append("could not find a student with nonacademic notes for Mi Panel historical-note check")

    # Docente comparativa should not calculate averages for extension group.
    status, comp = api_get("/api/dashboards/docente/grupos-comparativa", token)
    evidence["checks"]["docente_grupos_comparativa_status"] = status
    if status == 200:
        ext_group = next((g for g in comp.get("grupos", []) if g.get("codigo_grupo") == "EXTEXT2602000_20001"), None)
        evidence["checks"]["docente_comparativa_extension_group"] = ext_group
        if ext_group and (ext_group.get("periodos") or ext_group.get("promedio_actual") is not None):
            evidence["failures"].append("docente grupos-comparativa returned period/promedio data for extension group")
    else:
        evidence["failures"].append(f"docente grupos-comparativa returned status {status}")

    OUT.write_text(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    if evidence["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()