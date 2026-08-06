"""Focused verification for executive dashboard characterization/georeferencing bug.

Tests the real login + /api/dashboards/executive response against the expected
user-visible contract described in the bug report. Also prints source Excel and
MongoDB counts to make mismatches diagnosable.
"""
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd
import requests
from dotenv import dotenv_values
from pymongo import MongoClient


APP = Path("/app")
FRONTEND_ENV = dotenv_values(APP / "frontend" / ".env")
BACKEND_ENV = dotenv_values(APP / "backend" / ".env")
BASE_URL = (FRONTEND_ENV.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"
EMAIL = "lcorreaq@gmail.com"
PASSWORD = "IUDigital2026"


def norm(s):
    s = "" if s is None else str(s).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).upper()


def fmt_map(items, key):
    return {norm(i.get(key)): i.get("n", 0) for i in items}


def check(condition, label, details=None, failures=None):
    if condition:
        print(f"PASS: {label}")
        return True
    print(f"FAIL: {label}" + (f" -> {details}" if details is not None else ""))
    if failures is not None:
        failures.append({"label": label, "details": details})
    return False


def warn(condition, label, details=None, warnings=None):
    if condition:
        return False
    print(f"WARN: {label}" + (f" -> {details}" if details is not None else ""))
    if warnings is not None:
        warnings.append({"label": label, "details": details})
    return True


def excel_reference_counts():
    path = APP / "uploads_user" / "carac.xlsx"
    if not path.exists():
        print(f"WARN: Excel source not found at {path}")
        return {}
    df = pd.read_excel(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    if "doc_estudiante" in df.columns:
        df = df.drop_duplicates(subset=["doc_estudiante"])

    def value_counts(col):
        if col not in df.columns:
            return {}
        return Counter(str(v).strip() for v in df[col].fillna("") if str(v).strip())

    vivienda = value_counts("Tipo de vivienda")
    pais = value_counts("País residencia")
    depto = value_counts("Departamento residencia")
    vulner_raw = value_counts("Grupo vulnerable (si pertenece a uno)")

    print("\nSOURCE EXCEL COUNTS")
    print("Tipo de vivienda:", dict(vivienda.most_common()))
    print("País residencia top 10:", dict(pais.most_common(10)))
    print("Departamento residencia top 10:", dict(depto.most_common(10)))
    print("Grupo vulnerable raw top 15:", dict(vulner_raw.most_common(15)))
    return {"vivienda": vivienda, "pais": pais, "depto": depto, "vulner_raw": vulner_raw}


def mongo_reference_counts():
    mongo_url = BACKEND_ENV.get("MONGO_URL")
    db_name = BACKEND_ENV.get("DB_NAME")
    if not mongo_url or not db_name:
        print("WARN: Mongo env missing")
        return {}
    client = MongoClient(mongo_url)
    coll = client[db_name].students
    total = coll.count_documents({})
    rural_tipo_ubicacion = coll.count_documents({"tipo_ubicacion": {"$in": ["Rural", "Semirural"]}})
    vulnerable = coll.count_documents({"grupo_vulnerable": True})
    has_depto_res = coll.count_documents({"departamento_residencia": {"$exists": True, "$ne": None}})
    tipo_counts = list(coll.aggregate([
        {"$group": {"_id": "$tipo_ubicacion", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
    ]))
    depto_res_counts = list(coll.aggregate([
        {"$match": {"departamento_residencia": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$departamento_residencia", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$limit": 10},
    ]))
    vulnerability_counts = list(coll.aggregate([
        {"$match": {"grupo_vulnerable": True}},
        {"$group": {"_id": "$tipo_grupo_vulnerable", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$limit": 15},
    ]))
    print("\nMONGODB REFERENCE COUNTS")
    print("students total:", total)
    print("tipo_ubicacion Rural+Semirural:", rural_tipo_ubicacion)
    print("grupo_vulnerable True:", vulnerable)
    print("docs with departamento_residencia:", has_depto_res)
    print("tipo_ubicacion counts:", tipo_counts)
    print("departamento_residencia top 10:", depto_res_counts)
    print("tipo_grupo_vulnerable top 15:", vulnerability_counts)
    client.close()
    return {
        "total": total,
        "rural_tipo_ubicacion": rural_tipo_ubicacion,
        "vulnerable": vulnerable,
        "has_depto_res": has_depto_res,
    }


def main():
    failures = []
    warnings = []
    excel_counts = excel_reference_counts()
    mongo_counts = mongo_reference_counts()

    print(f"\nTesting API at {API}")
    login = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    print("login status:", login.status_code)
    if login.status_code != 200:
        print(login.text)
        return 2
    token = login.json()["access_token"]
    r = requests.get(f"{API}/dashboards/executive", headers={"Authorization": f"Bearer {token}"}, timeout=60)
    print("executive status:", r.status_code)
    if r.status_code != 200:
        print(r.text)
        return 2
    data = r.json()
    print("\nAPI RESPONSE SUMMARY")
    print(json.dumps({
        "kpis": data.get("kpis"),
        "by_ubicacion": data.get("by_ubicacion"),
        "by_edad": data.get("by_edad"),
        "by_vulnerabilidad": data.get("by_vulnerabilidad"),
        "by_pais": data.get("by_pais"),
        "by_departamento": data.get("by_departamento"),
    }, ensure_ascii=False, indent=2))

    k = data.get("kpis", {})
    by_ubicacion = fmt_map(data.get("by_ubicacion", []), "tipo")
    by_edad = fmt_map(data.get("by_edad", []), "rango")
    by_vuln = fmt_map(data.get("by_vulnerabilidad", []), "tipo")
    by_pais = fmt_map(data.get("by_pais", []), "pais")
    by_depto_items = data.get("by_departamento", [])
    by_depto = fmt_map(by_depto_items, "departamento")

    check(k.get("rurales") == 3404, "KPI rurales must be 3,404 from Tipo de vivienda Rural+Semirural", k.get("rurales"), failures)
    check(by_ubicacion.get("RURAL") == 3404,
          "Tipo de ubicación chart must be based on Tipo de vivienda with Rural+Semirural = 3,404", by_ubicacion, failures)
    warn(by_ubicacion.get("SEMIRURAL") == 143,
         "Tipo de ubicación chart collapses Semirural into Rural instead of showing Semirural as a separate vivienda category",
         by_ubicacion, warnings)
    check(2800 <= int(k.get("vulnerables") or 0) <= 2845,
          "KPI vulnerables must be approximately 2,821", k.get("vulnerables"), failures)

    required_age = {"MENOR 18", "18-22", "23-27", "28-32", "33-40", "41-50", "51+"}
    check(required_age.issubset(set(by_edad.keys())) and len(by_edad) >= 6,
          "by_edad must contain required age groups", by_edad, failures)

    expected_vuln_labels = [
        "VICTIMA CONFLICTO", "AFRO", "INDIGENA", "MADRE CABEZA", "LGBTI+",
        "POBREZA", "DISCAPACIDAD/PPL", "RURAL/CAMPESINO", "OTRO",
    ]
    missing_vuln = [label for label in expected_vuln_labels if label not in by_vuln]
    check(not missing_vuln, "by_vulnerabilidad must use normalized categories", {"missing": missing_vuln, "actual": by_vuln}, failures)
    check(1325 <= by_vuln.get("VICTIMA CONFLICTO", 0) <= 1395,
          "Víctima conflicto category count should be ~1,361", by_vuln, failures)
    check(200 <= by_vuln.get("AFRO", 0) <= 245 and 160 <= by_vuln.get("INDIGENA", 0) <= 195,
          "Afro and Indígena category counts should be normalized and approximate expected values", by_vuln, failures)

    check(by_pais.get("COLOMBIA") == 16425, "by_pais Colombia must be 16,425", by_pais, failures)
    exterior = {k: v for k, v in by_pais.items() if k and k != "COLOMBIA"}
    check(any("CANADA" in k for k in exterior) and "ARGENTINA" in exterior,
          "by_pais must include exterior countries such as Canadá and Argentina", exterior, failures)

    top5 = [norm(i.get("departamento")) for i in by_depto_items[:5]]
    expected_top5 = ["ANTIOQUIA", "MAGDALENA", "NARINO", "CAUCA", "GUAJIRA"]
    equivalent_top5 = ["ANTIOQUIA", "MAGDALENA", "NARINIO", "CAUCA", "GUAJIRA"]
    check(top5 in (expected_top5, equivalent_top5),
          "by_departamento top 5 must be Antioquia, Magdalena, Nariño/NARINIO, Cauca, Guajira", top5, failures)
    warn(top5 == expected_top5,
         "Departamento Nariño is rendered as NARINIO (source-data spelling), not the canonical Nariño label",
         top5, warnings)
    check(bool(by_depto), "by_departamento must not be empty", by_depto, failures)

    if excel_counts.get("vivienda"):
        expected_rural = excel_counts["vivienda"].get("Rural", 0) + excel_counts["vivienda"].get("Semirural", 0)
        check(expected_rural == 3404, "source Excel confirms Rural+Semirural = 3,404", expected_rural, failures)
    if mongo_counts:
        check(mongo_counts.get("rural_tipo_ubicacion") == 3404,
              "Mongo students.tipo_ubicacion is updated to source Tipo de vivienda values", mongo_counts, failures)
        check(mongo_counts.get("has_depto_res", 0) > 0,
              "Mongo students contain departamento_residencia used by API", mongo_counts, failures)

    print("\nWARNINGS:", json.dumps(warnings, ensure_ascii=False, indent=2))
    print("FAILURES:", json.dumps(failures, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())