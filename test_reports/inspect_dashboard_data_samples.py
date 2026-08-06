#!/usr/bin/env python3
"""Inspect sample records for apparent demo/simulated false positives and source vulnerable values."""
import json
import re
from pathlib import Path

from pymongo import MongoClient


def parse_env(path):
    out = {}
    for raw in Path(path).read_text().splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#") and "=" in raw:
            k, v = raw.split("=", 1)
            out[k] = v.strip().strip('"').strip("'")
    return out


env = parse_env("/app/backend/.env")
db = MongoClient(env["MONGO_URL"])[env["DB_NAME"]]
students = list(db.students.find(
    {"$or": [{"correo": re.compile(r"demo|example|test", re.I)}, {"nombre_completo": re.compile(r"demo|prueba|test", re.I)}]},
    {"_id": 0, "cedula": 1, "nombre_completo": 1, "correo": 1, "programa": 1},
).limit(20))
notes = list(db.historico_notas.find(
    {"$or": [{"estado": re.compile(r"simulad|demo|test|prueba", re.I)}, {"nombre_estudiante": re.compile(r"demo|test|prueba", re.I)}]},
    {"_id": 0, "cedula": 1, "nombre_estudiante": 1, "estado": 1, "periodo": 1, "asignatura_nombre": 1},
).limit(20))

source_vulnerable_value_counts = {}
try:
    import pandas as pd
    df = pd.read_excel("/app/uploads_user/carac.xlsx", sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]
    col = "Grupo vulnerable (si pertenece a uno)"
    if col in df.columns:
        source_vulnerable_value_counts = df[col].astype(str).str.strip().value_counts(dropna=False).head(20).to_dict()
except Exception as exc:
    source_vulnerable_value_counts = {"error": str(exc)}

print(json.dumps({
    "students_demo_like_samples": students,
    "notes_simulated_like_samples": notes,
    "source_vulnerable_value_counts_head": source_vulnerable_value_counts,
}, ensure_ascii=False, indent=2))