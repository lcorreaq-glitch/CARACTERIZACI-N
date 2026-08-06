#!/usr/bin/env python3
"""Small evidence extractor for the failing non-academic grupo-comparativa case."""
import json
from pymongo import MongoClient

db = MongoClient("mongodb://localhost:27017")["iudigital"]
g = db.grupos.find_one({"codigo_grupo": "PRECBH2602000_20003"}, {"_id": 0})
docs = list(
    db.historico_notas.find(
        {"docente_id": g.get("docente_id"), "codigo_asignatura": g.get("asignatura_codigo"), "periodo": "2026-1"},
        {"_id": 0, "cedula": 1, "periodo": 1, "nota": 1, "codigo_asignatura": 1, "programa": 1, "asignatura_nombre": 1, "docente_id": 1},
    ).limit(10)
)
print(json.dumps({"grupo": g, "matching_historico_sample": docs, "matching_count": len(docs)}, ensure_ascii=False, indent=2, default=str))