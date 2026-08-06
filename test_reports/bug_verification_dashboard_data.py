#!/usr/bin/env python3
"""Focused verification for dashboard real-data cleanup bug.

Checks login, executive/academic dashboard APIs, MongoDB source-of-truth
collections, and a sample student's period averages.
"""
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import requests


ROOT = Path("/app")
BACKEND_ENV = ROOT / "backend" / ".env"
FRONTEND_ENV = ROOT / "frontend" / ".env"


def parse_env(path):
    out = {}
    for raw in path.read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        out[k] = v.strip().strip('"').strip("'")
    return out


def approx(actual, expected, tol=0.02):
    return actual is not None and abs(float(actual) - float(expected)) <= tol


def add_assert(results, name, ok, detail):
    results.append({"name": name, "ok": bool(ok), "detail": detail})


def mongo_db():
    try:
        from pymongo import MongoClient
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"pymongo unavailable: {exc}")
    env = parse_env(BACKEND_ENV)
    client = MongoClient(env["MONGO_URL"], serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[env["DB_NAME"]]


def api_base():
    env = parse_env(FRONTEND_ENV)
    return env["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"


def login_and_fetch():
    base = api_base()
    s = requests.Session()
    login = s.post(
        base + "/auth/login",
        json={"email": "lcorreaq@gmail.com", "password": "IUDigital2026"},
        timeout=30,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    executive = s.get(base + "/dashboards/executive", headers=headers, timeout=60)
    academic = s.get(base + "/dashboards/academic", headers=headers, timeout=60)
    executive.raise_for_status()
    academic.raise_for_status()
    return login.json(), executive.json(), academic.json()


def db_period_stats(db):
    stats = {}
    pipe = [
        {"$group": {"_id": "$periodo", "n": {"$sum": 1}, "prom": {"$avg": "$nota"}, "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}}}},
        {"$sort": {"_id": 1}},
    ]
    for row in db.historico_notas.aggregate(pipe):
        n = row["n"]
        stats[row["_id"]] = {
            "n": n,
            "prom": round(row.get("prom") or 0, 2),
            "aprob_pct": round(row.get("aprob", 0) / n * 100, 1) if n else 0,
        }
    return stats


def academic_expected(db, field):
    pipe = [
        {"$group": {
            "_id": f"${field}",
            "n": {"$sum": 1},
            "con_notas": {"$sum": {"$cond": [{"$gt": ["$promedio", 0]}, 1, 0]}},
            "prom": {"$avg": {"$cond": [{"$gt": ["$promedio", 0]}, "$promedio", None]}},
            "prom_2025_2": {"$avg": {"$cond": [{"$gt": ["$promedio_2025_2", 0]}, "$promedio_2025_2", None]}},
            "prom_2026_1": {"$avg": {"$cond": [{"$gt": ["$promedio_2026_1", 0]}, "$promedio_2026_1", None]}},
        }},
        {"$project": {"_id": 1, "n": 1, "con_notas": 1,
                      "prom": {"$round": [{"$ifNull": ["$prom", 0]}, 2]},
                      "prom_2025_2": {"$round": [{"$ifNull": ["$prom_2025_2", 0]}, 2]},
                      "prom_2026_1": {"$round": [{"$ifNull": ["$prom_2026_1", 0]}, 2]}}},
    ]
    return {r["_id"]: {k: r.get(k) for k in ["n", "con_notas", "prom", "prom_2025_2", "prom_2026_1"]} for r in db.students.aggregate(pipe)}


def source_file_counts():
    """Best-effort independent counts from uploaded Excel for characterization flags."""
    try:
        import pandas as pd
    except Exception as exc:
        return {"error": f"pandas unavailable: {exc}"}
    carac = ROOT / "uploads_user" / "carac.xlsx"
    if not carac.exists():
        return {"error": "missing /app/uploads_user/carac.xlsx"}
    df = pd.read_excel(carac, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]
    def norm(v):
        if pd.isna(v) or v is None:
            return ""
        return str(v).strip()
    def true_text(v):
        s = norm(v).lower()
        return bool(s) and s not in ("no", "no aplica", "ninguno", "ninguna", "n/a", "sin dato", "")
    victim_col = "Ubicación de conflicto"
    vuln_col = "Grupo vulnerable (si pertenece a uno)"
    disc_col = "Tipo de discapacidad"
    dir_col = "Dirección residencia"
    rural = 0
    if dir_col in df.columns:
        for v in df[dir_col]:
            s = norm(v).upper()
            if any(k in s for k in ("VEREDA", "CORREGIMIENTO", "RURAL")):
                rural += 1
    return {
        "total_rows": int(len(df)),
        "victimas_from_file": int(sum(true_text(v) for v in df[victim_col])) if victim_col in df.columns else None,
        "vulnerables_from_file": int(sum(true_text(v) for v in df[vuln_col])) if vuln_col in df.columns else None,
        "discapacidad_from_file": int(sum(true_text(v) for v in df[disc_col])) if disc_col in df.columns else None,
        "rurales_from_direccion_file": int(rural),
    }


def main():
    results = []
    artifacts = {}
    login, executive, academic = login_and_fetch()
    db = mongo_db()
    k = executive.get("kpis", {})
    artifacts["api_kpis"] = k
    artifacts["api_academic_facultades"] = academic.get("by_facultad", [])
    artifacts["periods_in_historico_notas"] = db_period_stats(db)
    artifacts["source_file_counts"] = source_file_counts()

    add_assert(results, "login_superadmin", login.get("user", {}).get("email") == "lcorreaq@gmail.com", login.get("user", {}))

    # User-requested clean real data KPIs. Victimas checked both against review value and source-file value below.
    expected_kpis = {
        "total": 16461,
        "matriculados": 14244,
        "rurales": 1918,
        "vulnerables": 2853,
        "discapacidad": 202,
        "programas": 21,
        "facultades": 5,
    }
    for key, expected in expected_kpis.items():
        add_assert(results, f"executive_kpi_{key}", k.get(key) == expected, {"actual": k.get(key), "expected": expected})
    add_assert(results, "executive_kpi_victimas_review_expected_4852", k.get("victimas") == 4852, {"actual": k.get("victimas"), "expected": 4852})

    expected_periods = {
        "2025-2": {"prom": 3.45, "n": 84871, "aprob_pct": 76.0},
        "2026-1": {"prom": 3.12, "n": 84505, "aprob_pct": 68.0},
    }
    for period, exp in expected_periods.items():
        p_key = period.replace("-", "_")
        add_assert(results, f"executive_notas_{period}", k.get(f"notas_{p_key}") == exp["n"], {"actual": k.get(f"notas_{p_key}"), "expected": exp["n"]})
        add_assert(results, f"executive_promedio_{period}", approx(k.get(f"promedio_{p_key}"), exp["prom"], 0.03), {"actual": k.get(f"promedio_{p_key}"), "expected_approx": exp["prom"]})
        add_assert(results, f"executive_aprob_pct_{period}", approx(k.get(f"aprob_pct_{p_key}"), exp["aprob_pct"], 1.0), {"actual": k.get(f"aprob_pct_{p_key}"), "expected_approx": exp["aprob_pct"]})
    add_assert(results, "no_historico_notas_2026_2", "2026-2" not in artifacts["periods_in_historico_notas"], artifacts["periods_in_historico_notas"])

    # DB cleanliness and API-vs-DB consistency.
    db_counts = {
        "students": db.students.count_documents({}),
        "matriculados": db.students.count_documents({"estado_matricula": "Estudiante Matriculado"}),
        "rurales": db.students.count_documents({"tipo_ubicacion": {"$in": ["Rural", "Semirural"]}}),
        "victimas": db.students.count_documents({"victima_conflicto": True}),
        "vulnerables": db.students.count_documents({"grupo_vulnerable": True}),
        "discapacidad": db.students.count_documents({"discapacidad_flag": True}),
        "programas": len(db.students.distinct("programa")),
        "facultades": len(db.students.distinct("facultad")),
        "docentes_demo_extra": db.users.count_documents({"role": "docente", "$and": [{"email": re.compile(r"demo", re.I)}, {"email": {"$ne": "docente.demo@iudigital.edu.co"}}]}),
        "docente_demo_allowed": db.users.count_documents({"role": "docente", "email": "docente.demo@iudigital.edu.co"}),
        # Avoid substring false positives in real surnames/emails (e.g. demonaci, montes).
        "students_demo_like": db.students.count_documents({"$or": [{"correo": re.compile(r"(^|[._-])(demo|test|prueba)([._@-]|$)", re.I)}, {"nombre_completo": re.compile(r"\b(demo|prueba|test)\b", re.I)}]}),
        "notas_simuladas_like": db.historico_notas.count_documents({"$or": [{"estado": re.compile(r"simulad|demo", re.I)}, {"nombre_estudiante": re.compile(r"\b(demo|test)\b|simulad", re.I)}]}),
    }
    artifacts["db_counts"] = db_counts
    for api_key, db_key in [("total", "students"), ("matriculados", "matriculados"), ("rurales", "rurales"), ("victimas", "victimas"), ("vulnerables", "vulnerables"), ("discapacidad", "discapacidad"), ("programas", "programas"), ("facultades", "facultades")]:
        add_assert(results, f"api_matches_db_{api_key}", k.get(api_key) == db_counts[db_key], {"api": k.get(api_key), "db": db_counts[db_key]})
    add_assert(results, "no_extra_demo_docentes", db_counts["docentes_demo_extra"] == 0, db_counts)
    add_assert(results, "no_demo_students_like", db_counts["students_demo_like"] == 0, db_counts)
    add_assert(results, "no_simulated_notes_like", db_counts["notas_simuladas_like"] == 0, db_counts)

    sf = artifacts["source_file_counts"]
    if not sf.get("error"):
        add_assert(results, "source_total_matches_api", sf.get("total_rows") == k.get("total"), {"source": sf.get("total_rows"), "api": k.get("total")})
        add_assert(results, "source_victimas_matches_api", sf.get("victimas_from_file") == k.get("victimas"), {"source": sf.get("victimas_from_file"), "api": k.get("victimas")})
        add_assert(results, "source_vulnerables_matches_api", sf.get("vulnerables_from_file") == k.get("vulnerables"), {"source": sf.get("vulnerables_from_file"), "api": k.get("vulnerables")})
        add_assert(results, "source_discapacidad_matches_api", sf.get("discapacidad_from_file") == k.get("discapacidad"), {"source": sf.get("discapacidad_from_file"), "api": k.get("discapacidad")})
        add_assert(results, "source_rurales_matches_api", sf.get("rurales_from_direccion_file") == k.get("rurales"), {"source": sf.get("rurales_from_direccion_file"), "api": k.get("rurales")})

    # Academic endpoint schema and counts.
    by_fac = academic.get("by_facultad", [])
    by_prog = academic.get("by_program_avg", [])
    expected_faculties = {"FCEAC", "FCyH", "FICA", "FE", "Sin facultad asignada"}
    actual_faculties = {r.get("facultad") for r in by_fac}
    required_fields = {"n", "con_notas", "prom", "prom_2025_2", "prom_2026_1"}
    add_assert(results, "academic_facultad_count", len(by_fac) == 5, {"actual": len(by_fac), "faculties": sorted(map(str, actual_faculties))})
    abbrev_present = {
        "FCEAC": any("FCEAC" in str(v) for v in actual_faculties),
        "FCyH": any("FCyH" in str(v) for v in actual_faculties),
        "FICA": any("FICA" in str(v) for v in actual_faculties),
        "FE": any("FE" in str(v) for v in actual_faculties),
        "Sin facultad asignada": "Sin facultad asignada" in actual_faculties,
    }
    add_assert(results, "academic_facultad_real_names", all(abbrev_present.values()), {"actual": sorted(map(str, actual_faculties)), "expected_abbrev_present": abbrev_present})
    add_assert(results, "academic_facultad_fields", all(required_fields.issubset(r) for r in by_fac), by_fac[:2])
    add_assert(results, "academic_program_count", len(by_prog) == 21, {"actual": len(by_prog)})
    add_assert(results, "academic_program_fields", all(required_fields.issubset(r) for r in by_prog), by_prog[:2])

    exp_fac = academic_expected(db, "facultad")
    mismatches = []
    for row in by_fac:
        expected = exp_fac.get(row.get("facultad"))
        if expected:
            for f in required_fields:
                if row.get(f) != expected.get(f):
                    mismatches.append({"facultad": row.get("facultad"), "field": f, "api": row.get(f), "db_expected": expected.get(f)})
    add_assert(results, "academic_facultad_excludes_zero_averages_matches_db", not mismatches, mismatches[:10])

    # Pick one real student with both periods and compare stored per-period averages to historico_notas.
    sample = db.students.find_one({"promedio_2025_2": {"$gt": 0}, "promedio_2026_1": {"$gt": 0}}, {"_id": 0, "cedula": 1, "promedio_2025_2": 1, "promedio_2026_1": 1})
    sample_expected = {}
    if sample:
        for period in ("2025-2", "2026-1"):
            rows = list(db.historico_notas.aggregate([
                {"$match": {"cedula": sample["cedula"], "periodo": period}},
                {"$group": {"_id": None, "avg": {"$avg": "$nota"}, "n": {"$sum": 1}}},
            ]))
            sample_expected[period] = {"avg": round(rows[0]["avg"], 2), "n": rows[0]["n"]} if rows else None
        add_assert(results, "sample_student_period_averages_populated", True, {"student": sample, "expected_from_notes": sample_expected})
        add_assert(results, "sample_student_2025_2_avg_matches_notes", approx(sample.get("promedio_2025_2"), sample_expected["2025-2"]["avg"], 0.01), {"student": sample, "expected": sample_expected})
        add_assert(results, "sample_student_2026_1_avg_matches_notes", approx(sample.get("promedio_2026_1"), sample_expected["2026-1"]["avg"], 0.01), {"student": sample, "expected": sample_expected})
    else:
        add_assert(results, "sample_student_period_averages_populated", False, "No student found with both promedio_2025_2 and promedio_2026_1 > 0")

    failures = [r for r in results if not r["ok"]]
    output = {"ok": not failures, "results": results, "failures": failures, "artifacts": artifacts}
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())