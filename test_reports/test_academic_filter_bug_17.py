#!/usr/bin/env python3
"""Iteration 17 focused backend verification for academic-note filtering bug.

User contract: notas/promedios must exclude Extensión Académica and
Inglés Fuera de la Malla across dashboards/tableros.
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

import requests
from pymongo import MongoClient


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8001")
EMAIL = os.environ.get("TEST_EMAIL", "lcorreaq@gmail.com")
PASSWORD = os.environ.get("TEST_PASSWORD", "IUDigital2026")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "iudigital")
OUT_JSON = Path("/app/test_reports/academic_filter_iteration_17_evidence.json")

NON_ACAD_RE = re.compile(
    r"(extensi[oó]n\s+acad[eé]mica|^curso\s|diplomad|fuera\s+de\s+la\s+malla|-\s+extens)",
    re.IGNORECASE,
)
TARGET_GROUP = "PRECBH2602000_20003"
EXTENSION_GROUP = "EXTEXT2602000_20001"
HIST_STUDENT = "1000063303"


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


def round2(value):
    return round(float(value or 0), 2)


class Runner:
    def __init__(self):
        self.session = requests.Session()
        self.db = MongoClient(MONGO_URL)[DB_NAME]
        self.failures = []
        self.minor = []
        self.evidence = {}

    def pass_(self, check, detail):
        print(f"PASS {check}: {detail}")

    def fail(self, check, detail):
        self.failures.append({"check": check, "detail": detail})
        print(f"FAIL {check}: {detail}")

    def warn(self, check, detail):
        self.minor.append({"check": check, "detail": detail})
        print(f"WARN {check}: {detail}")

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
            self.fail("login", f"missing access_token body={r.text[:500]}")
            return False
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.pass_("login", f"authenticated {EMAIL}")
        return True

    def get(self, path):
        r = self.session.get(f"{BASE_URL}{path}", timeout=120)
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
            self.fail("db_baseline", "no non-academic historico_notas rows exist, cannot prove exclusion")
        else:
            self.pass_("db_baseline", f"raw={raw_total}, academic={academic_total}, excluded={non_academic_total}")

    def check_admin_grupos_final_fix(self):
        list_data = self.get(f"/api/admin/grupos?codigo_grupo={quote(TARGET_GROUP)}")
        if list_data is not None:
            items = list_data.get("items")
            self.evidence["admin_grupos_target_list"] = list_data
            if items != []:
                self.fail("admin.grupos.target.items_empty", f"expected items=[], got {items}")
            else:
                self.pass_("admin.grupos.target.items_empty", "items=[] for non-academic outside-malla group")
            if list_data.get("total") not in (0, None):
                self.warn("admin.grupos.target.total", f"items=[] but total={list_data.get('total')} (pagination count not post-filtered)")

        detail = self.get(f"/api/admin/grupos/{quote(TARGET_GROUP)}")
        if detail is not None:
            notas = detail.get("notas_por_periodo")
            self.evidence["admin_grupos_target_detail"] = {
                "grupo": detail.get("grupo"),
                "notas_por_periodo": notas,
            }
            if notas != []:
                self.fail("admin.grupos.target.detail_notas_empty", f"expected notas_por_periodo=[], got {notas}")
            else:
                self.pass_("admin.grupos.target.detail_notas_empty", "notas_por_periodo=[] for outside-malla group detail")

        # Sanity check another known extension group when present.
        ext_list = self.get(f"/api/admin/grupos?codigo_grupo={quote(EXTENSION_GROUP)}")
        if ext_list is not None:
            self.evidence["admin_grupos_extension_list"] = ext_list
            if ext_list.get("items") not in ([], None):
                self.fail("admin.grupos.extension.items_empty", f"expected no extension group items, got {ext_list.get('items')}")
            else:
                self.pass_("admin.grupos.extension.items_empty", "extension group list is suppressed/empty")

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
            self.pass_("historical.series_periodo", f"academic-only stats {api_stats}")
        bad_programs = [r.get("programa") for r in data.get("by_program", []) if is_non_academic(r.get("programa"), "")]
        if bad_programs:
            self.fail("historical.by_program", f"non-academic programas returned: {bad_programs[:10]}")
        else:
            self.pass_("historical.by_program", "no non-academic program rows")
        self.evidence["historical_api_stats"] = api_stats

    def check_docente_student_history(self):
        raw_bad = self.db.historico_notas.count_documents({
            "cedula": HIST_STUDENT,
            "$or": [
                {"codigo_asignatura": {"$regex": r"^EXT", "$options": "i"}},
                {"programa": {"$regex": NON_ACAD_RE.pattern, "$options": "i"}},
            ],
        })
        data = self.get(f"/api/dashboards/docente/estudiante/{HIST_STUDENT}/historico")
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
            self.pass_("docente.estudiante.historico", f"returned {len(notas)} academic notes; raw_bad_notes_in_db={raw_bad}")
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
            self.pass_("executive.kpis", f"academic-only KPI values {got}")
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
            self.pass_("academic.default_total", f"default total academic-only {default_total}")
        if include is not None and include_total != raw_total:
            self.fail("academic.include_extension", f"include_total={include_total}, DB raw_total={raw_total}")
        elif include is not None:
            self.pass_("academic.include_extension", f"include_extension raw comparison total {include_total}")
        bad_program_rows = []
        for key in ("by_program_avg", "by_program_regular", "by_program_ingles", "by_program_extension"):
            for row in default.get(key, []):
                if is_non_academic(row.get("programa"), ""):
                    bad_program_rows.append({"section": key, "programa": row.get("programa"), "n": row.get("n")})
        if bad_program_rows:
            self.fail("academic.program_sections", f"non-academic program rows returned: {bad_program_rows[:10]}")
        else:
            self.pass_("academic.program_sections", "default academic dashboard has no non-academic program rows")
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
                    self.pass_("academic.facultad_filter", f"facultad={faculty!r} API matches DB academic total {api_total}")
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
                    self.pass_("historical.program_filter", f"program={program!r} API matches DB academic stats")

    def check_docente_grupos_comparativa(self):
        data = self.get("/api/dashboards/docente/grupos-comparativa")
        if data is None:
            return
        grupos = data.get("grupos", [])
        target = [g for g in grupos if g.get("codigo_grupo") == TARGET_GROUP]
        bad_groups = [
            {"codigo_grupo": g.get("codigo_grupo"), "asignatura_codigo": g.get("asignatura_codigo"), "programa": g.get("programa"), "periodos": g.get("periodos")}
            for g in grupos
            if is_non_academic(g.get("programa"), g.get("asignatura_codigo"))
        ]
        if target:
            self.fail("docente.grupos_comparativa.target", f"{TARGET_GROUP} still returned: {target[:1]}")
        else:
            self.pass_("docente.grupos_comparativa.target", f"{TARGET_GROUP} absent")
        if bad_groups:
            self.fail("docente.grupos_comparativa.non_academic_groups", f"non-academic groups returned: {bad_groups[:10]}")
        else:
            self.pass_("docente.grupos_comparativa.non_academic_groups", f"{len(grupos)} groups returned; none non-academic")
        self.evidence["grupos_comparativa"] = {"total_groups": len(grupos), "target_count": len(target), "bad_group_count": len(bad_groups)}

    def check_admin_docente_grupos_endpoint(self):
        """Additional comprehensive tablero check discovered in admin_router.

        This endpoint returns historical note averages per docente group and must not
        leak non-academic group averages either.
        """
        target = self.db.grupos.find_one({"codigo_grupo": TARGET_GROUP}, {"_id": 0})
        if not target or not target.get("docente_id"):
            self.warn("admin.docentes.grupos.setup", f"target group {TARGET_GROUP} missing or has no docente_id")
            return
        docente_id = target["docente_id"]
        data = self.get(f"/api/admin/docentes/{quote(docente_id)}/grupos")
        if data is None:
            return
        bad = []
        target_rows = []
        for g in data:
            row = {
                "codigo_grupo": g.get("codigo_grupo"),
                "asignatura_codigo": g.get("asignatura_codigo"),
                "programa": g.get("programa"),
                "historico_notas": g.get("historico_notas"),
            }
            if g.get("codigo_grupo") == TARGET_GROUP:
                target_rows.append(row)
            if is_non_academic(g.get("programa"), g.get("asignatura_codigo")) and g.get("historico_notas"):
                bad.append(row)
        self.evidence["admin_docente_grupos"] = {
            "docente_id": docente_id,
            "total_groups": len(data),
            "target_rows": target_rows,
            "non_academic_with_historico_count": len(bad),
            "sample_bad": bad[:5],
        }
        if bad:
            self.fail("admin.docentes.grupos.non_academic_historico", f"non-academic groups returned with historico_notas/promedios: {bad[:5]}")
        else:
            self.pass_("admin.docentes.grupos.non_academic_historico", "no non-academic group historical averages returned")

    def run(self):
        if not self.login():
            return False
        self.establish_db_baseline()
        self.check_admin_grupos_final_fix()
        self.check_historical()
        self.check_docente_student_history()
        self.check_executive()
        self.check_academic()
        self.check_faculty_and_program_filters()
        self.check_docente_grupos_comparativa()
        self.check_admin_docente_grupos_endpoint()
        OUT_JSON.write_text(json.dumps({"failures": self.failures, "minor": self.minor, "evidence": self.evidence}, ensure_ascii=False, indent=2, default=str))
        print(f"Wrote evidence to {OUT_JSON}")
        print("EVIDENCE_JSON_START")
        print(json.dumps({"failures": self.failures, "minor": self.minor, "evidence": self.evidence}, ensure_ascii=False, indent=2, default=str))
        print("EVIDENCE_JSON_END")
        return not self.failures


if __name__ == "__main__":
    sys.exit(0 if Runner().run() else 1)