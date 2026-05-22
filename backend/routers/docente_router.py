"""Docente dashboard: vista restringida a sus materias y estudiantes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from database import db

router = APIRouter(prefix="/api/dashboards/docente", tags=["dashboards-docente"])


async def _docente_materias(user_id: str):
    """Return docente_materia rows with materia/programa enrichment."""
    items = await db.docente_materia.find({"docente_id": user_id}, {"_id": 0}).to_list(500)
    enriched = []
    for it in items:
        materia = await db.materias.find_one({"id": it["materia_id"]}, {"_id": 0}) or {}
        programa_id = materia.get("programa_id") or it.get("programa_id")
        programa = None
        if programa_id:
            programa = await db.programas.find_one({"id": programa_id}, {"_id": 0})
        enriched.append({
            **it,
            "materia_nombre": materia.get("nombre", "—"),
            "materia_codigo": materia.get("codigo"),
            "programa_id": programa_id,
            "programa_nombre": programa.get("nombre") if programa else None,
        })
    return enriched


@router.get("/me")
async def my_overview(user=Depends(get_current_user)):
    if user.get("role") not in ("docente", "superadmin", "admin"):
        raise HTTPException(403, "Solo docentes")

    materias = await _docente_materias(user["id"])
    if not materias:
        return {
            "materias": [],
            "kpis": {"total_estudiantes": 0, "promedio": 0, "en_riesgo": 0, "excelencia": 0},
            "programas_asociados": [],
        }

    # Build student match: union of programs of assigned materias
    program_names = set()
    for m in materias:
        if m.get("programa_nombre"):
            program_names.add(m["programa_nombre"])
    match = {"programa": {"$in": list(program_names)}} if program_names else {}

    coll = db.students
    total = await coll.count_documents(match) if match else 0
    if total == 0:
        return {
            "materias": materias,
            "kpis": {"total_estudiantes": 0, "promedio": 0, "en_riesgo": 0, "excelencia": 0},
            "programas_asociados": list(program_names),
        }

    pipeline = [{"$match": match}]
    agg = await coll.aggregate(pipeline + [{"$group": {
        "_id": None,
        "total": {"$sum": 1},
        "matriculados": {"$sum": {"$cond": [{"$eq": ["$estado_matricula", "Estudiante Matriculado"]}, 1, 0]}},
        "promedio": {"$avg": "$promedio"},
        "vulnerables": {"$sum": {"$cond": ["$grupo_vulnerable", 1, 0]}},
        "victimas": {"$sum": {"$cond": ["$victima_conflicto", 1, 0]}},
        "discapacidad": {"$sum": {"$cond": ["$discapacidad_flag", 1, 0]}},
        "avance_pct": {"$avg": "$avance_pct"},
    }}]).to_list(1)

    en_riesgo = await coll.count_documents({**match, "promedio": {"$lt": 3.0, "$gt": 0}})
    excelencia = await coll.count_documents({**match, "promedio": {"$gte": 4.5}})

    distribucion = await coll.aggregate(pipeline + [
        {"$bucket": {
            "groupBy": "$promedio",
            "boundaries": [0, 1, 2, 3, 3.5, 4, 4.5, 5.01],
            "default": "Otros",
            "output": {"n": {"$sum": 1}}
        }}
    ]).to_list(50)

    by_programa = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$programa", "n": {"$sum": 1}, "prom": {"$avg": "$promedio"}}},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "programa": "$_id", "n": 1, "prom": {"$round": ["$prom", 2]}}}
    ]).to_list(50)

    caracterizacion = {
        "genero": await coll.aggregate(pipeline + [
            {"$group": {"_id": "$genero", "n": {"$sum": 1}}},
            {"$project": {"_id": 0, "genero": "$_id", "n": 1}}
        ]).to_list(10),
        "estrato": await coll.aggregate(pipeline + [
            {"$group": {"_id": "$estrato", "n": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
            {"$project": {"_id": 0, "estrato": "$_id", "n": 1}}
        ]).to_list(10),
        "ubicacion": await coll.aggregate(pipeline + [
            {"$group": {"_id": "$tipo_ubicacion", "n": {"$sum": 1}}},
            {"$project": {"_id": 0, "tipo": "$_id", "n": 1}}
        ]).to_list(10),
    }

    municipios = await coll.aggregate(pipeline + [
        {"$group": {
            "_id": {"codigo": "$ciudad_codigo", "nombre": "$ciudad_nombre",
                    "lat": "$lat", "lon": "$lon", "departamento": "$departamento"},
            "n": {"$sum": 1},
            "prom": {"$avg": "$promedio"}
        }},
        {"$sort": {"n": -1}},
        {"$limit": 200},
        {"$project": {"_id": 0, "codigo": "$_id.codigo", "nombre": "$_id.nombre",
                      "lat": "$_id.lat", "lon": "$_id.lon",
                      "departamento": "$_id.departamento",
                      "n": 1, "prom": {"$round": ["$prom", 2]}}}
    ]).to_list(200)

    k = agg[0] if agg else {}
    return {
        "materias": materias,
        "programas_asociados": list(program_names),
        "kpis": {
            "total_estudiantes": k.get("total", 0),
            "matriculados": k.get("matriculados", 0),
            "promedio": round(k.get("promedio", 0) or 0, 2),
            "avance_pct": round(k.get("avance_pct", 0) or 0, 1),
            "en_riesgo": en_riesgo,
            "excelencia": excelencia,
            "vulnerables": k.get("vulnerables", 0),
            "victimas": k.get("victimas", 0),
            "discapacidad": k.get("discapacidad", 0),
        },
        "distribucion_notas": distribucion,
        "by_programa": by_programa,
        "caracterizacion": caracterizacion,
        "municipios": municipios,
    }


@router.get("/students")
async def my_students(
    materia_id: Optional[str] = None,
    riesgo: Optional[bool] = None,
    user=Depends(get_current_user),
):
    """Lista paginada de estudiantes para el docente, opcionalmente filtrada."""
    if user.get("role") not in ("docente", "superadmin", "admin"):
        raise HTTPException(403, "Solo docentes")

    materias = await _docente_materias(user["id"])
    program_names = set()
    if materia_id:
        # Filter only to that materia's program
        m = next((x for x in materias if x["materia_id"] == materia_id), None)
        if m and m.get("programa_nombre"):
            program_names.add(m["programa_nombre"])
    else:
        for m in materias:
            if m.get("programa_nombre"):
                program_names.add(m["programa_nombre"])

    if not program_names:
        return {"students": [], "total": 0}

    match = {"programa": {"$in": list(program_names)}}
    if riesgo:
        match["promedio"] = {"$lt": 3.0, "$gt": 0}

    students = await db.students.find(
        match,
        {"_id": 0, "cedula": 1, "nombre": 1, "apellidos": 1, "correo": 1,
         "programa": 1, "nivel": 1, "promedio": 1, "estado_matricula": 1,
         "ciudad_nombre": 1, "departamento": 1, "grupo_vulnerable": 1,
         "victima_conflicto": 1, "discapacidad_flag": 1, "tipo_ubicacion": 1}
    ).sort("promedio", 1).limit(200).to_list(200)
    total = await db.students.count_documents(match)
    return {"students": students, "total": total}
