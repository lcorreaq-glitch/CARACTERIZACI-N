#!/usr/bin/env python3
"""Focused backend verification for academic-note filtering bug.

Contract: dashboard notas/promedios must exclude Extensión Académica and
Inglés Fuera de la Malla across dashboard endpoints.
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


def is_non_academic(programa, codigo):
    programa = programa or ""
    codigo = codigo or ""
    return codigo.upper().startswith("EXT") or bool(NON_ACAD_RE.search(programa))


def round2(v):
    return round(float(v or 0), 2)


class CheckRunner:
    def __init__(self):
        self.session = requests.Session()
        self.failures = []
        self.evidence = {}
        self.db = MongoClient(MONGO_URL)[DB_NAME]

    def fail(self, name, detail):
        self.failures.append({"check": name, "detail": detail})
        print(f"FAIL {name}: {detail}")

    def ok(self, name, detail):
        print(f"PASS {name}: {detail}")

    def login(self):
        r = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
            timeout=30,
        )
        if r.status_code != 200:
            self.fail("login", f"status={r.status_code} body={r.text[:300]}")
            return False
        token = r.json().get("access_token")
        if not token:
            self.fail("login", "no access_token in response")
            return False
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.ok("login", f"authenticated as {EMAIL}")
        return True

    def get(self, path):
        r = self.session.get(f"{BASE_URL}{path}", timeout=60)
        if r.status_code != 200:
            self.fail(path, f"status={r.status_code} body={r.text[:500]}")
            return None
        return r.json()

    def db_period_stats(self, match):
        out = {}
        for row in self.db.historico_notas.aggregate(
            [
                {"$match": match},
                {
                    "$group": {
                        "_id": "$periodo",
                        "prom": {"$avg": "$nota"},
                        "n_notas": {"$sum": 1},
                        "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
                        "cedulas": {"$addToSet": "$cedula"},
                    }
                },
            ]
        ):
            n = row["n_notas"]
            out[row["_id"]] = {
                "n_notas": n,
                "promedio": round2(row["prom"]),
                "tasa_aprobacion": round(float(row["aprob"]) / n * 100, 1) if n else 0,
                "matriculados": len(row.get("cedulas", [])),
            }
        return out

    def check_historical(self):
        data = self.get("/api/dashboards/historical")
        if data is None:
            return
        series = {x["periodo"]: x for x in data.get("series_periodo", [])}
        expected_hard = {
            "2025-2": {"n_notas": 82155, "promedio": 3.48},
            "2026-1": {"n_notas": 82036, "promedio": 3.17},
        }
        raw_forbidden = {
            "2025-2": {"n_notas": 84871, "promedio": 3.45},
            "2026-1": {"n_notas": 84505, "promedio": 3.12},
        }
        db_expected = self.db_period_stats(academic_notes_match())
        for per, exp in expected_hard.items():
            row = series.get(per)
            if not row:
                self.fail("historical.series_periodo", f"missing periodo {per}")
                continue
            got = {"n_notas": row.get("n_notas"), "promedio": row.get("promedio")}
            if got != exp:
                self.fail("historical.series_periodo", f"{per} got {got}, expected {exp}")
            elif got == raw_forbidden[per]:
                self.fail("historical.series_periodo", f"{per} still has raw forbidden values {got}")
            else:
                self.ok("historical.series_periodo", f"{per} academic-only {got}")
            if per in db_expected and (
                row.get("n_notas") != db_expected[per]["n_notas"]
                or row.get("promedio") != db_expected[per]["promedio"]
            ):
                self.fail("historical.db_compare", f"{per} API={row} DB_expected={db_expected[per]}")
        bad_programs = [
            p.get("programa")
            for p in data.get("by_program", [])
            if is_non_academic(p.get("programa"), "")
        ]
        if bad_programs:
            self.fail("historical.by_program", f"non-academic programas returned: {bad_programs[:10]}")
        else:
            self.ok("historical.by_program", "no extension/fuera-de-malla programs returned")
        self.evidence["historical_series"] = series

        # Edge case: explicit non-academic programa filter must not return notes.
        sample = self.db.historico_notas.find_one(
            {"programa": {"$regex": r"fuera\s+de\s+la\s+malla|extensi[oó]n|^curso\s|diplomad", "$options": "i"}},
            {"_id": 0, "programa": 1},
        )
        if sample and sample.get("programa"):
            prog = sample["programa"]
            filt = self.get(f"/api/dashboards/historical?programa={quote(prog)}")
            if filt is not None and (filt.get("series_periodo") or filt.get("by_program")):
                self.fail("historical.non_academic_program_filter", f"{prog!r} returned data: {filt}")
            else:
                self.ok("historical.non_academic_program_filter", f"{prog!r} returned no academic notes")

    def check_docente_student(self):
        cedula = "1000063303"
        raw_bad = self.db.historico_notas.count_documents(
            {
                "cedula": cedula,
                "$or": [
                    {"codigo_asignatura": {"$regex": r"^EXT", "$options": "i"}},
                    {"programa": {"$regex": NON_ACAD_RE.pattern, "$options": "i"}},
                ],
            }
        )
        data = self.get(f"/api/dashboards/docente/estudiante/{cedula}/historico")
        if data is None:
            return
        notas = []
        for per in data.get("periodos", []):
            notas.extend(per.get("notas", []))
        bad = [
            {"periodo": n.get("periodo"), "codigo": n.get("codigo_asignatura"), "programa": n.get("programa")}
            for n in notas
            if is_non_academic(n.get("programa"), n.get("codigo_asignatura"))
        ]
        if bad:
            self.fail("docente.estudiante.historico", f"returned non-academic notes: {bad[:10]}")
        else:
            self.ok(
                "docente.estudiante.historico",
                f"returned {len(notas)} academic notes and 0 non-academic; raw_bad_notes_in_db={raw_bad}",
            )
        self.evidence["docente_student"] = {"total_api_notes": len(notas), "raw_bad_notes_in_db": raw_bad}

    def check_executive(self):
        data = self.get("/api/dashboards/executive")
        if data is None:
            return
        k = data.get("kpis", {})
        expected = {
            "promedio": 3.32,
            "notas_2025_2": 82155,
            "notas_2026_1": 82036,
            "promedio_2025_2": 3.48,
            "promedio_2026_1": 3.17,
        }
        got = {key: k.get(key) for key in expected}
        if got != expected:
            self.fail("executive.kpis", f"got {got}, expected {expected}")
        elif k.get("promedio") == 3.28:
            self.fail("executive.kpis", "promedio still equals raw forbidden 3.28")
        else:
            self.ok("executive.kpis", f"academic-only KPI values {got}")
        self.evidence["executive_kpis"] = got

    def check_academic(self):
        data = self.get("/api/dashboards/academic")
        if data is None:
            return
        estados_total = sum(int(row.get("total", 0)) for row in data.get("estados_por_periodo", []))
        period_totals = {row.get("periodo"): row.get("total") for row in data.get("estados_por_periodo", [])}
        bad_program_rows = []
        for key in ("by_program_avg", "by_program_regular", "by_program_ingles", "by_program_extension"):
            for row in data.get(key, []):
                if is_non_academic(row.get("programa"), ""):
                    bad_program_rows.append({"section": key, "programa": row.get("programa"), "n": row.get("n")})
        if estados_total != 164191:
            self.fail("academic.estados_por_periodo", f"total={estados_total}, expected academic-only 164191 (not raw 169376); per={period_totals}")
        elif estados_total == 169376:
            self.fail("academic.estados_por_periodo", "still returns raw total 169376")
        else:
            self.ok("academic.estados_por_periodo", f"academic-only total={estados_total}, per={period_totals}")
        if bad_program_rows:
            self.fail("academic.by_program", f"non-academic program rows returned: {bad_program_rows[:10]}")
        else:
            self.ok("academic.by_program", "no non-academic program rows in academic dashboard")
        self.evidence["academic"] = {
            "kpis": data.get("kpis", {}),
            "estados_total": estados_total,
            "period_totals": period_totals,
            "by_program_ingles_len": len(data.get("by_program_ingles", [])),
            "by_program_extension_len": len(data.get("by_program_extension", [])),
        }

    def check_grupos(self):
        data = self.get("/api/dashboards/docente/grupos-comparativa")
        if data is None:
            return
        grupos = data.get("grupos", [])
        bad_with_periodos = [
            {
                "codigo_grupo": g.get("codigo_grupo"),
                "asignatura_codigo": g.get("asignatura_codigo"),
                "programa": g.get("programa"),
                "periodos": g.get("periodos"),
            }
            for g in grupos
            if g.get("periodos") and is_non_academic(g.get("programa"), g.get("asignatura_codigo"))
        ]
        if bad_with_periodos:
            self.fail("docente.grupos_comparativa", f"non-academic groups still have period averages: {bad_with_periodos[:10]}")
        else:
            self.ok("docente.grupos_comparativa", f"{len(grupos)} groups returned; no non-academic group has period averages")
        # Compare one returned academic group's period stats to direct academic-only DB aggregate.
        sample = next((g for g in grupos if g.get("periodos") and not is_non_academic(g.get("programa"), g.get("asignatura_codigo"))), None)
        if sample:
            stats = {}
            for row in self.db.historico_notas.aggregate(
                [
                    {
                        "$match": academic_notes_match(
                            {"docente_id": sample.get("docente_id"), "codigo_asignatura": sample.get("asignatura_codigo")}
                        )
                    },
                    {"$group": {"_id": "$periodo", "prom": {"$avg": "$nota"}, "n": {"$sum": 1}}},
                ]
            ):
                stats[row["_id"]] = {"promedio": round2(row["prom"]), "total": row["n"]}
            for p in sample.get("periodos", []):
                exp = stats.get(p.get("periodo"))
                if exp and (p.get("promedio") != exp["promedio"] or p.get("total") != exp["total"]):
                    self.fail("docente.grupos_comparativa.db_compare", f"sample={sample.get('codigo_grupo')} periodo={p.get('periodo')} API={p} DB={exp}")
                    break
            else:
                self.ok("docente.grupos_comparativa.db_compare", f"sample group {sample.get('codigo_grupo')} matches academic-only DB stats")
        self.evidence["grupos"] = {"total_groups": len(grupos), "bad_with_periodos": len(bad_with_periodos)}

    def check_faculty_program_filters(self):
        # Edge case requested by user: calculations by carrera/facultad must also exclude non-academic notes.
        faculty = self.db.students.find_one({"facultad": {"$nin": [None, ""]}}, {"_id": 0, "facultad": 1})
        program = self.db.students.find_one({"programa": {"$nin": [None, ""]}}, {"_id": 0, "programa": 1})
        if faculty and faculty.get("facultad"):
            fac = faculty["facultad"]
            data = self.get(f"/api/dashboards/academic?facultad={quote(fac)}")
            if data is not None:
                cedulas = self.db.students.distinct("cedula", {"facultad": fac})
                db_total = self.db.historico_notas.count_documents(academic_notes_match({"cedula": {"$in": cedulas}}))
                api_total = sum(int(row.get("total", 0)) for row in data.get("estados_por_periodo", []))
                if api_total != db_total:
                    self.fail("academic.facultad_filter", f"facultad={fac!r} API total={api_total}, DB academic total={db_total}")
                else:
                    self.ok("academic.facultad_filter", f"facultad={fac!r} API matches DB academic total={api_total}")
        if program and program.get("programa"):
            prog = program["programa"]
            data = self.get(f"/api/dashboards/historical?programa={quote(prog)}")
            if data is not None:
                db_stats = self.db_period_stats(academic_notes_match({"programa": prog}))
                api_stats = {r.get("periodo"): {"n_notas": r.get("n_notas"), "promedio": r.get("promedio")} for r in data.get("series_periodo", [])}
                expected_stats = {k: {"n_notas": v["n_notas"], "promedio": v["promedio"]} for k, v in db_stats.items()}
                if api_stats != expected_stats:
                    self.fail("historical.programa_filter", f"programa={prog!r} API={api_stats}, DB academic={expected_stats}")
                else:
                    self.ok("historical.programa_filter", f"programa={prog!r} API matches DB academic stats")

    def run(self):
        if not self.login():
            return False
        self.check_historical()
        self.check_docente_student()
        self.check_executive()
        self.check_academic()
        self.check_grupos()
        self.check_faculty_program_filters()
        print("\nEVIDENCE_JSON_START")
        print(json.dumps({"failures": self.failures, "evidence": self.evidence}, ensure_ascii=False, indent=2, default=str))
        print("EVIDENCE_JSON_END")
        return not self.failures


if __name__ == "__main__":
    ok = CheckRunner().run()
    sys.exit(0 if ok else 1)