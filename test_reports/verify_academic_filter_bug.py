#!/usr/bin/env python3
"""Focused backend verification for academic averages excluding extension/English-out-of-plan notes."""
import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from pymongo import MongoClient


APP = Path("/app")
FRONT_ENV = APP / "frontend" / ".env"
BACK_ENV = APP / "backend" / ".env"
OUT = APP / "test_reports" / "academic_filter_evidence.json"


def read_env(path):
    vals = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        vals[k] = v.strip().strip('"').strip("'")
    return vals


front_env = read_env(FRONT_ENV)
back_env = read_env(BACK_ENV)
BASE = front_env["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = back_env.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = back_env.get("DB_NAME", "iudigital")

NON_ACADEMIC_RE = r"(extensi[oó]n\s+acad[eé]mica|^curso\s|diplomad|fuera\s+de\s+la\s+malla|-\s+extens)"
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
EVALUATED_STATES = ["Aprobada", "Reprobada", "Habilitada-Aprobada", "Habilitada-Reprobada"]
TEST_GROUP = "EXTEXT2602000_20001"


def round2(x):
    return round(float(x or 0), 2)


def api_get(path, token, **params):
    r = requests.get(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=60,
    )
    return {"status": r.status_code, "json": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text}


def agg_avg_count(coll, match):
    row = list(coll.aggregate([
        {"$match": match},
        {"$group": {"_id": None, "avg": {"$avg": "$nota"}, "count": {"$sum": 1}}},
    ]))
    return {"count": row[0]["count"] if row else 0, "avg": row[0]["avg"] if row else 0, "avg_round": round2(row[0]["avg"] if row else 0)}


def period_stats(coll, match):
    rows = list(coll.aggregate([
        {"$match": match},
        {"$group": {"_id": "$periodo", "avg": {"$avg": "$nota"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]))
    return {r["_id"]: {"count": r["count"], "avg_round": round2(r["avg"])} for r in rows}


def combine_match(*parts):
    ands = []
    base = {}
    for p in parts:
        if not p:
            continue
        if "$and" in p:
            ands.extend(p["$and"])
            base.update({k: v for k, v in p.items() if k != "$and"})
        else:
            ands.append(p)
    if base and ands:
        return {**base, "$and": ands}
    if ands:
        return {"$and": ands}
    return base


def sum_estados_totals(payload):
    return sum(int(r.get("total", 0)) for r in payload.get("estados_por_periodo", []))


def nonacademic_programs(program_rows):
    bad = []
    rx = re.compile(NON_ACADEMIC_RE, re.I)
    for row in program_rows:
        p = row.get("programa") or ""
        if rx.search(p):
            bad.append(p)
    return sorted(set(bad))[:20]


def main():
    evidence = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "base_url": BASE,
        "db": DB_NAME,
        "checks": {},
        "failures": [],
        "warnings": [],
    }

    login = requests.post(
        f"{BASE}/api/auth/login",
        json={"email": "lcorreaq@gmail.com", "password": "IUDigital2026"},
        timeout=30,
    )
    evidence["checks"]["login_status"] = login.status_code
    login.raise_for_status()
    token = login.json()["access_token"]

    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    hn = db.historico_notas

    raw_all = agg_avg_count(hn, {})
    academic_all = agg_avg_count(hn, ACADEMIC_MATCH)
    raw_periods = period_stats(hn, {})
    academic_periods = period_stats(hn, ACADEMIC_MATCH)
    nonacademic_count = raw_all["count"] - academic_all["count"]
    evidence["checks"]["db_raw_all_notes"] = raw_all
    evidence["checks"]["db_academic_all_notes"] = academic_all
    evidence["checks"]["db_nonacademic_excluded_count"] = nonacademic_count
    evidence["checks"]["db_raw_periods"] = raw_periods
    evidence["checks"]["db_academic_periods"] = academic_periods

    # Executive dashboard checks.
    executive = api_get("/api/dashboards/executive", token)
    evidence["checks"]["executive_status"] = executive["status"]
    if executive["status"] != 200:
        evidence["failures"].append(f"executive status {executive['status']}")
    else:
        kpis = executive["json"].get("kpis", {})
        evidence["checks"]["executive_kpis_subset"] = {
            "promedio": kpis.get("promedio"),
            "promedio_2025_2": kpis.get("promedio_2025_2"),
            "promedio_2026_1": kpis.get("promedio_2026_1"),
            "notas_2025_2": kpis.get("notas_2025_2"),
            "notas_2026_1": kpis.get("notas_2026_1"),
        }
        if kpis.get("promedio") != academic_all["avg_round"]:
            evidence["failures"].append(f"executive promedio {kpis.get('promedio')} != DB academic {academic_all['avg_round']}")
        for per, api_key_avg, api_key_n in [("2025-2", "promedio_2025_2", "notas_2025_2"), ("2026-1", "promedio_2026_1", "notas_2026_1")]:
            expected = academic_periods.get(per, {})
            if expected:
                if kpis.get(api_key_avg) != expected.get("avg_round"):
                    evidence["failures"].append(f"executive {api_key_avg} {kpis.get(api_key_avg)} != DB academic {expected.get('avg_round')}")
                if kpis.get(api_key_n) != expected.get("count"):
                    evidence["failures"].append(f"executive {api_key_n} {kpis.get(api_key_n)} != DB academic {expected.get('count')}")
        if kpis.get("promedio") == raw_all["avg_round"] and raw_all["avg_round"] != academic_all["avg_round"]:
            evidence["failures"].append("executive promedio still matches raw/include-extension average")

    # Academic dashboard include_extension=false vs true.
    academic_false = api_get("/api/dashboards/academic", token)
    academic_true = api_get("/api/dashboards/academic", token, include_extension="true")
    evidence["checks"]["academic_statuses"] = {"default_false": academic_false["status"], "include_true": academic_true["status"]}
    if academic_false["status"] != 200 or academic_true["status"] != 200:
        evidence["failures"].append("academic endpoint returned non-200")
    else:
        af = academic_false["json"]
        at = academic_true["json"]
        false_estado_total = sum_estados_totals(af)
        true_estado_total = sum_estados_totals(at)
        evaluated_raw = agg_avg_count(hn, {"estado": {"$in": EVALUATED_STATES}})
        evaluated_academic = agg_avg_count(hn, combine_match(ACADEMIC_MATCH, {"estado": {"$in": EVALUATED_STATES}}))
        evidence["checks"]["academic_counts"] = {
            "default_estados_total": false_estado_total,
            "include_extension_estados_total": true_estado_total,
            "expected_academic_all_notes": academic_all["count"],
            "expected_raw_all_notes": raw_all["count"],
            "difference": true_estado_total - false_estado_total,
            "default_notas_evaluadas": af.get("kpis", {}).get("notas_evaluadas"),
            "include_true_notas_evaluadas": at.get("kpis", {}).get("notas_evaluadas"),
            "expected_evaluated_academic": evaluated_academic,
            "expected_evaluated_raw": evaluated_raw,
            "default_promedio_global": af.get("kpis", {}).get("promedio_global"),
            "include_true_promedio_global": at.get("kpis", {}).get("promedio_global"),
        }
        if false_estado_total != academic_all["count"]:
            evidence["failures"].append(f"academic default estados total {false_estado_total} != DB academic notes {academic_all['count']}")
        if true_estado_total != raw_all["count"]:
            evidence["failures"].append(f"academic include_extension total {true_estado_total} != DB raw notes {raw_all['count']}")
        if af.get("kpis", {}).get("notas_evaluadas") != evaluated_academic["count"]:
            evidence["failures"].append("academic default notas_evaluadas does not match academic evaluated DB count")
        if af.get("kpis", {}).get("promedio_global") != evaluated_academic["avg_round"]:
            evidence["failures"].append("academic default promedio_global does not match academic evaluated DB average")
        bad_programs = nonacademic_programs(af.get("by_program_avg", []))
        evidence["checks"]["academic_bad_nonacademic_programs_in_by_program_avg"] = bad_programs
        if bad_programs:
            evidence["failures"].append(f"academic default by_program_avg contains nonacademic programs: {bad_programs[:5]}")

    # Groups extension case: extension-only group should expose no historical promedio/notas.
    grupos = api_get("/api/admin/grupos", token, codigo_grupo=TEST_GROUP, limit="5")
    detail = api_get(f"/api/admin/grupos/{TEST_GROUP}", token)
    evidence["checks"]["grupos_status"] = grupos["status"]
    evidence["checks"]["grupo_detail_status"] = detail["status"]
    if grupos["status"] != 200:
        evidence["failures"].append(f"grupos status {grupos['status']}")
    else:
        items = grupos["json"].get("items", [])
        evidence["checks"]["grupos_test_group"] = items[0] if items else None
        if not items:
            evidence["warnings"].append(f"test group {TEST_GROUP} not found in /admin/grupos")
        else:
            g = items[0]
            if g.get("notas_historico") not in (0, None) or g.get("promedio_historico") not in (None, 0):
                evidence["failures"].append(f"extension group has historical academic notes/promedio: n={g.get('notas_historico')} prom={g.get('promedio_historico')}")
    if detail["status"] != 200:
        evidence["failures"].append(f"grupo detail status {detail['status']}")
    else:
        notas_por_periodo = detail["json"].get("notas_por_periodo", [])
        evidence["checks"]["grupo_detail_notas_por_periodo"] = notas_por_periodo
        if notas_por_periodo:
            evidence["failures"].append(f"extension group detail returned notas_por_periodo: {notas_por_periodo}")

    # Student promedio recomputation from latest academic period.
    periods = sorted([p for p in hn.distinct("periodo") if p])
    latest = periods[-1] if periods else None
    evidence["checks"]["latest_period"] = latest
    if latest:
        latest_academic_match = combine_match(ACADEMIC_MATCH, {"periodo": latest})
        rows = list(hn.aggregate([
            {"$match": latest_academic_match},
            {"$group": {"_id": "$cedula", "prom": {"$avg": "$nota"}, "total": {"$sum": 1}, "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}}}},
        ]))
        mismatches = []
        missing_students_count = 0
        checked_existing_students = 0
        for r in rows:
            student = db.students.find_one({"cedula": r["_id"]}, {"_id": 0, "cedula": 1, "promedio": 1, "total_materias": 1, "aprobadas": 1})
            if not student:
                # Some historical-note cedulas are not present in students; that is data coverage, not proof
                # that the recompute is wrong for existing dashboard students.
                missing_students_count += 1
                continue
            checked_existing_students += 1
            expected_prom = round2(r.get("prom"))
            if student.get("promedio") != expected_prom or student.get("total_materias") != r.get("total") or student.get("aprobadas") != r.get("aprob"):
                mismatches.append({
                    "cedula": r["_id"],
                    "expected_promedio": expected_prom,
                    "actual_promedio": student.get("promedio"),
                    "expected_total": r.get("total"),
                    "actual_total": student.get("total_materias"),
                    "expected_aprobadas": r.get("aprob"),
                    "actual_aprobadas": student.get("aprobadas"),
                })
                if len(mismatches) >= 20:
                    break
        evidence["checks"]["student_recompute"] = {
            "academic_cedulas_latest_period": len(rows),
            "checked_existing_students": checked_existing_students,
            "historico_cedulas_missing_from_students": missing_students_count,
            "mismatch_sample_count": len(mismatches),
            "mismatches_sample": mismatches[:20],
        }
        if mismatches:
            evidence["failures"].append(f"students.promedio/latest academic recompute mismatches found (sample {len(mismatches)})")

    # Existing startup log proof (do not restart services from this test).
    log_hits = []
    for log_path in [Path("/var/log/supervisor/backend.out.log"), Path("/var/log/supervisor/backend.err.log")]:
        if not log_path.exists():
            continue
        try:
            for line in log_path.read_text(errors="ignore").splitlines():
                if "Recomputado promedio académico" in line:
                    log_hits.append({"file": str(log_path), "line": line[-500:]})
        except Exception as exc:
            evidence["warnings"].append(f"could not read {log_path}: {exc}")
    evidence["checks"]["startup_log_hits"] = log_hits[-5:]
    if not log_hits:
        evidence["failures"].append("startup recompute log message not found in supervisor backend logs")

    OUT.write_text(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    if evidence["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()