#!/usr/bin/env python3
"""Focused backend verification for academic-note filtering bug (iteration 16).

Contract: dashboard notas/promedios must exclude Extensión Académica and
Inglés Fuera de la Malla across affected dashboard/API endpoints.
"""

import json
import os
import re
import sys
from urllib.parse import quote

import requests
from pymongo import MongoClient


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8001")
EMAIL = os.environ.get("TEST_EMAIL", "lcorreaq@gmail.com")
PASSWORD = os.environ.get("TEST_PASSWORD", "IUDigital2026")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "iudigital")

NON_ACAD_RE = re.compile(
    r"(extensi[oó]n\s+acad[eé]mica|^curso\s|diplomad|fuera\s+de\s+la\s+malla|-\s+extens)",
    re.IGNORECASE,
)


def academic_notes_match(base=None):
    m = dict(base or {})
    academic_conditions = [
        {"codigo_asignatura": {"$not": {"$regex": r"^EXT", "$options": "i"}}},
        {
            "$or": [
                {"programa": {"$exists": False}},
                {"programa": None},
                {"programa": ""},
                {"programa": {"$not": {"$regex": NON_ACAD_RE.pattern, "$options": "i"}}},
            ]
        },
    ]
    if "$and" in m:
        m["$and"] = list(m["$and"]) + academic_conditions
    else:
        m["$and"] = academic_conditions
    return m


def is_non_academic(programa=None, codigo=None):
    programa = programa or ""
    codigo = codigo or ""
    return codigo.upper().startswith("EXT") or bool(NON_ACAD_RE.search(programa))


def round2(v):
    return round(float(v or 0), 2)


class Runner:
    def __init__(self):
        self.session = requests.Session()
        self.db = MongoClient(MONGO_URL)[DB_NAME]
        self.failures = []
        self.evidence = {}

    def ok(self, check, detail):
        print(f"PASS {check}: {detail}")

    def fail(self, check, detail):
        self.failures.append({"check": check, "detail": detail})
        print(f"FAIL {check}: {detail}")

    def login(self):
        r = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
            timeout=30,
        )
        if r.status_code != 200:
            self.fail("login", f"status={r.status_code} body={r.text[:500]}")
            return False
        token = r.json().get("access_token")
        if not token:
            self.fail("login", f"no token body={r.text[:500]}")
            return False
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.ok("login", f"authenticated {EMAIL}")
        return True

    def get(self, path):
        r = self.session.get(f"{BASE_URL}{path}", timeout=90)
        if r.status_code != 200:
            self.fail(path, f"status={r.status_code} body={r.text[:500]}")
            return None
        return r.json()

    def db_period_stats(self, match):
        out = {}
        for row in self.db.historico_notas.aggregate([
            {"$match": match},
            {"$group": {
                "_id": "$periodo",
                "prom": {"$avg": "$nota"},
                "n_notas": {"$sum": 1},
                "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
                "cedulas": {"$addToSet": "$cedula"},
            }},
        ]):
            n = row["n_notas"]
            out[row["_id"]] = {
                "n_notas": n,
                "promedio": round2(row["prom"]),
                "tasa_aprobacion": round(float(row["aprob"]) / n * 100, 1) if n else 0,
                "matriculados": len(row.get("cedulas", [])),
            }
        return out

    def establish_db_baseline(self):
        raw_total = self.db.historico_notas.count_documents({})
        academic_total = self.db.historico_notas.count_documents(academic_notes_match())
        non_academic_total = raw_total - academic_total
        raw_avg = list(self.db.historico_notas.aggregate([
            {"$group": {"_id": None, "avg": {"$avg": "$nota"}}}
        ]))[0]["avg"]
        academic_avg = list(self.db.historico_notas.aggregate([
            {"$match": academic_notes_match()},
            {"$group": {"_id": None, "avg": {"$avg": "$nota"}}},
        ]))[0]["avg"]
        self.evidence["db_baseline"] = {
            "raw_total": raw_total,
            "academic_total": academic_total,
            "non_academic_total": non_academic_total,
            "raw_avg": round2(raw_avg),
            "academic_avg": round2(academic_avg),
            "academic_period_stats": self.db_period_stats(academic_notes_match()),
            "raw_period_stats": self.db_period_stats({}),
        }
        if non_academic_total <= 0:
            self.fail("db_baseline", "no non-academic rows in DB; cannot prove exclusion")
        else:
            self.ok("db_baseline", f"raw={raw_total}, academic={academic_total}, excluded={non_academic_total}")

    def check_grupos_comparativa(self):
        data = self.get("/api/dashboards/docente/grupos-comparativa")
        if data is None:
            return
        grupos = data.get("grupos", [])
        target = [g for g in grupos if g.get("codigo_grupo") == "PRECBH2602000_20003"]
        bad_groups = [
            {"codigo_grupo": g.get("codigo_grupo"), "asignatura_codigo": g.get("asignatura_codigo"), "programa": g.get("programa"), "periodos": g.get("periodos")}
            for g in grupos
            if is_non_academic(g.get("programa"), g.get("asignatura_codigo"))
        ]
        if target:
            self.fail("docente.grupos_comparativa.target", f"PRECBH2602000_20003 still returned: {target[:1]}")
        else:
            self.ok("docente.grupos_comparativa.target", "PRECBH2602000_20003 not present")
        if bad_groups:
            self.fail("docente.grupos_comparativa.non_academic_groups", f"non-academic groups returned: {bad_groups[:10]}")
        else:
            self.ok("docente.grupos_comparativa.non_academic_groups", f"{len(grupos)} groups returned; none with EXT* or fuera de la malla/extensión program")
        self.evidence["grupos_comparativa"] = {"total_groups": len(grupos), "target_count": len(target), "bad_group_count": len(bad_groups)}

    def check_historical(self):
        data = self.get("/api/dashboards/historical")
        if data is None:
            return
        api_stats = {r.get("periodo"): {"n_notas": r.get("n_notas"), "promedio": r.get("promedio")} for r in data.get("series_periodo", [])}
        expected_stats = {k: {"n_notas": v["n_notas"], "promedio": v["promedio"]} for k, v in self.db_period_stats(academic_notes_match()).items()}
        hard_expected = {"2025-2": {"n_notas": 82155, "promedio": 3.48}, "2026-1": {"n_notas": 82036, "promedio": 3.17}}
        if api_stats != expected_stats:
            self.fail("historical.series_periodo", f"API={api_stats}, DB academic={expected_stats}")
        elif {k: api_stats.get(k) for k in hard_expected} != hard_expected:
            self.fail("historical.series_periodo.hard_values", f"got={api_stats}, expected={hard_expected}")
        else:
            self.ok("historical.series_periodo", f"academic-only stats {api_stats}")
        bad_programs = [r.get("programa") for r in data.get("by_program", []) if is_non_academic(r.get("programa"), "")]
        if bad_programs:
            self.fail("historical.by_program", f"non-academic programas returned: {bad_programs[:10]}")
        else:
            self.ok("historical.by_program", "no non-academic program rows")
        sample_bad_program = self.db.historico_notas.find_one(
            {"programa": {"$regex": NON_ACAD_RE.pattern, "$options": "i"}},
            {"_id": 0, "programa": 1},
        )
        if sample_bad_program:
            prog = sample_bad_program["programa"]
            filtered = self.get(f"/api/dashboards/historical?programa={quote(prog)}")
            if filtered and (filtered.get("series_periodo") or filtered.get("by_program")):
                self.fail("historical.non_academic_program_filter", f"programa={prog!r} returned {filtered}")
            else:
                self.ok("historical.non_academic_program_filter", f"programa={prog!r} returned no data")
        self.evidence["historical_api_stats"] = api_stats

    def check_docente_student_history(self):
        cedula = "1000063303"
        raw_bad = self.db.historico_notas.count_documents({
            "cedula": cedula,
            "$or": [
                {"codigo_asignatura": {"$regex": r"^EXT", "$options": "i"}},
                {"programa": {"$regex": NON_ACAD_RE.pattern, "$options": "i"}},
            ],
        })
        data = self.get(f"/api/dashboards/docente/estudiante/{cedula}/historico")
        if data is None:
            return
        notas = [n for p in data.get("periodos", []) for n in p.get("notas", [])]
        bad = [
            {"periodo": n.get("periodo"), "codigo_asignatura": n.get("codigo_asignatura"), "programa": n.get("programa"), "asignatura_nombre": n.get("asignatura_nombre")}
            for n in notas
            if is_non_academic(n.get("programa"), n.get("codigo_asignatura"))
        ]
        if bad:
            self.fail("docente.estudiante.historico", f"returned non-academic notes: {bad[:10]}")
        else:
            self.ok("docente.estudiante.historico", f"returned {len(notas)} academic notes; raw_bad_notes_in_db={raw_bad}")
        self.evidence["docente_student_history"] = {"api_total_notes": len(notas), "raw_bad_notes_in_db": raw_bad}

    def check_executive(self):
        data = self.get("/api/dashboards/executive")
        if data is None:
            return
        kpis = data.get("kpis", {})
        expected = {
            "promedio": 3.32,
            "notas_2025_2": 82155,
            "notas_2026_1": 82036,
            "promedio_2025_2": 3.48,
            "promedio_2026_1": 3.17,
        }
        got = {k: kpis.get(k) for k in expected}
        if got != expected:
            self.fail("executive.kpis", f"got={got}, expected={expected}")
        else:
            self.ok("executive.kpis", f"academic-only KPI values {got}")
        self.evidence["executive_kpis"] = got

    def check_academic(self):
        default = self.get("/api/dashboards/academic")
        include = self.get("/api/dashboards/academic?include_extension=true")
        if default is None:
            return
        default_total = sum(int(r.get("total", 0)) for r in default.get("estados_por_periodo", []))
        include_total = sum(int(r.get("total", 0)) for r in include.get("estados_por_periodo", [])) if include else None
        academic_total = self.evidence["db_baseline"]["academic_total"]
        raw_total = self.evidence["db_baseline"]["raw_total"]
        if default_total != academic_total:
            self.fail("academic.default_total", f"default_total={default_total}, DB academic_total={academic_total}")
        else:
            self.ok("academic.default_total", f"default total academic-only {default_total}")
        if include is not None and include_total != raw_total:
            self.fail("academic.include_extension", f"include_total={include_total}, DB raw_total={raw_total}")
        elif include is not None:
            self.ok("academic.include_extension", f"include_extension exposes raw comparison total {include_total}")
        bad_program_rows = []
        for key in ("by_program_avg", "by_program_regular", "by_program_ingles", "by_program_extension"):
            for row in default.get(key, []):
                if is_non_academic(row.get("programa"), ""):
                    bad_program_rows.append({"section": key, "programa": row.get("programa"), "n": row.get("n")})
        if bad_program_rows:
            self.fail("academic.program_sections", f"non-academic program rows returned: {bad_program_rows[:10]}")
        else:
            self.ok("academic.program_sections", "default academic dashboard has no non-academic program rows")
        self.evidence["academic"] = {"default_total": default_total, "include_extension_total": include_total, "kpis": default.get("kpis", {})}

    def check_faculty_and_program_filters(self):
        faculty_doc = self.db.students.find_one({"facultad": {"$nin": [None, ""]}}, {"_id": 0, "facultad": 1})
        if faculty_doc:
            faculty = faculty_doc["facultad"]
            data = self.get(f"/api/dashboards/academic?facultad={quote(faculty)}")
            if data is not None:
                cedulas = self.db.students.distinct("cedula", {"facultad": faculty})
                expected_total = self.db.historico_notas.count_documents(academic_notes_match({"cedula": {"$in": cedulas}}))
                api_total = sum(int(r.get("total", 0)) for r in data.get("estados_por_periodo", []))
                if api_total != expected_total:
                    self.fail("academic.facultad_filter", f"facultad={faculty!r} API={api_total}, DB academic={expected_total}")
                else:
                    self.ok("academic.facultad_filter", f"facultad={faculty!r} API matches DB academic total {api_total}")
        program_doc = self.db.students.find_one({"programa": {"$nin": [None, ""]}}, {"_id": 0, "programa": 1})
        if program_doc:
            program = program_doc["programa"]
            data = self.get(f"/api/dashboards/historical?programa={quote(program)}")
            if data is not None:
                expected = {k: {"n_notas": v["n_notas"], "promedio": v["promedio"]} for k, v in self.db_period_stats(academic_notes_match({"programa": program})).items()}
                api = {r.get("periodo"): {"n_notas": r.get("n_notas"), "promedio": r.get("promedio")} for r in data.get("series_periodo", [])}
                if api != expected:
                    self.fail("historical.program_filter", f"program={program!r} API={api}, DB academic={expected}")
                else:
                    self.ok("historical.program_filter", f"program={program!r} API matches DB academic stats")

    def check_admin_grupos(self):
        # Previously fixed endpoint: averages/notas on group listings must not be produced for non-academic groups.
        checks = ["EXTEXT2602000_20001", "PRECBH2602000_20003"]
        results = {}
        for codigo in checks:
            data = self.get(f"/api/admin/grupos?codigo_grupo={quote(codigo)}")
            if data is None:
                continue
            items = data.get("items", [])
            results[codigo] = items[:3]
            for item in items:
                non_acad_group = is_non_academic(item.get("programa"), item.get("asignatura_codigo"))
                has_stats = bool(item.get("notas_historico")) or item.get("promedio_historico") not in (None, 0)
                if non_acad_group and has_stats:
                    self.fail("admin.grupos.non_academic_stats", f"{codigo} returned non-academic group with stats: {item}")
                elif non_acad_group:
                    self.ok("admin.grupos.non_academic_stats", f"{codigo} returned no promedio/notas stats for non-academic group")
        self.evidence["admin_grupos"] = results

    def run(self):
        if not self.login():
            return False
        self.establish_db_baseline()
        self.check_grupos_comparativa()
        self.check_historical()
        self.check_docente_student_history()
        self.check_executive()
        self.check_academic()
        self.check_faculty_and_program_filters()
        self.check_admin_grupos()
        print("\nEVIDENCE_JSON_START")
        print(json.dumps({"failures": self.failures, "evidence": self.evidence}, ensure_ascii=False, indent=2, default=str))
        print("EVIDENCE_JSON_END")
        return not self.failures


if __name__ == "__main__":
    sys.exit(0 if Runner().run() else 1)