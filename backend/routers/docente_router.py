"""Docente dashboard v2 — restringido a sus grupos asignados con panel de riesgo académico."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from auth import get_current_user
from database import db

router = APIRouter(prefix="/api/dashboards/docente", tags=["dashboards-docente"])


async def _my_groups(user):
    """Return groups where this user is the docente, plus admin bypass."""
    if user.get("role") in ("superadmin", "admin"):
        # optional docente_id filter via query would be added at endpoint level; here return all
        return await db.grupos.find({}, {"_id": 0}).to_list(5000)
    return await db.grupos.find({"docente_id": user["id"]}, {"_id": 0}).to_list(1000)


async def _cedulas_de_mis_grupos(user, codigo_grupo: Optional[str] = None):
    """Cédulas matriculadas en los grupos del docente. Opcionalmente filtra a un grupo específico."""
    groups = await _my_groups(user)
    codigos = [g["codigo_grupo"] for g in groups]
    if codigo_grupo:
        if codigo_grupo not in codigos and user.get("role") not in ("superadmin", "admin"):
            raise HTTPException(403, "No tienes acceso a este grupo")
        codigos = [codigo_grupo]
    if not codigos:
        return set()
    cedulas = await db.matriculas.distinct("cedula", {"codigo_grupo": {"$in": codigos}})
    return set(cedulas)


@router.get("/me")
async def my_overview(codigo_grupo: Optional[str] = None, user=Depends(get_current_user)):
    if user.get("role") not in ("docente", "superadmin", "admin"):
        raise HTTPException(403, "Solo docentes")

    groups = await _my_groups(user)
    if not groups:
        return {
            "grupos": [], "kpis": {"total_estudiantes": 0, "promedio": 0, "en_riesgo": 0, "excelencia": 0},
        }

    cedulas = await _cedulas_de_mis_grupos(user, codigo_grupo)
    if not cedulas:
        return {"grupos": groups, "kpis": {"total_estudiantes": 0, "promedio": 0, "en_riesgo": 0, "excelencia": 0}}

    match = {"cedula": {"$in": list(cedulas)}}
    total = await db.students.count_documents(match)

    agg = await db.students.aggregate([
        {"$match": match},
        {"$group": {
            "_id": None,
            "promedio": {"$avg": "$promedio"},
            "vulnerables": {"$sum": {"$cond": ["$grupo_vulnerable", 1, 0]}},
            "victimas": {"$sum": {"$cond": ["$victima_conflicto", 1, 0]}},
            "discapacidad": {"$sum": {"$cond": ["$discapacidad_flag", 1, 0]}},
            "avance_pct": {"$avg": "$avance_pct"},
        }}
    ]).to_list(1)
    en_riesgo = await db.students.count_documents({**match, "promedio": {"$lt": 3.0, "$gt": 0}})
    excelencia = await db.students.count_documents({**match, "promedio": {"$gte": 4.5}})

    by_programa = await db.students.aggregate([
        {"$match": match},
        {"$group": {"_id": "$programa", "n": {"$sum": 1}, "prom": {"$avg": "$promedio"}}},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "programa": "$_id", "n": 1, "prom": {"$round": ["$prom", 2]}}}
    ]).to_list(50)

    caracterizacion = {}
    for field in ("genero", "estrato", "tipo_ubicacion", "sisben_nivel", "grupo_sisben"):
        caracterizacion[field] = await db.students.aggregate([
            {"$match": match},
            {"$group": {"_id": f"${field}", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
            {"$project": {"_id": 0, "label": "$_id", "n": 1}}
        ]).to_list(15)

    municipios = await db.students.aggregate([
        {"$match": match},
        {"$group": {
            "_id": {"codigo": "$ciudad_codigo", "nombre": "$ciudad_nombre",
                    "lat": "$lat", "lon": "$lon", "departamento": "$departamento"},
            "n": {"$sum": 1}, "prom": {"$avg": "$promedio"}}},
        {"$sort": {"n": -1}}, {"$limit": 200},
        {"$project": {"_id": 0, "codigo": "$_id.codigo", "nombre": "$_id.nombre",
                      "lat": "$_id.lat", "lon": "$_id.lon", "departamento": "$_id.departamento",
                      "n": 1, "prom": {"$round": ["$prom", 2]}}}
    ]).to_list(200)

    k = agg[0] if agg else {}
    return {
        "grupos": groups,
        "kpis": {
            "total_estudiantes": total,
            "promedio": round(k.get("promedio", 0) or 0, 2),
            "avance_pct": round(k.get("avance_pct", 0) or 0, 1),
            "en_riesgo": en_riesgo,
            "excelencia": excelencia,
            "vulnerables": k.get("vulnerables", 0),
            "victimas": k.get("victimas", 0),
            "discapacidad": k.get("discapacidad", 0),
        },
        "by_programa": by_programa,
        "caracterizacion": caracterizacion,
        "municipios": municipios,
    }


@router.get("/en-riesgo")
async def estudiantes_en_riesgo(
    codigo_grupo: Optional[str] = None,
    umbral: float = Query(3.0, ge=0, le=5),
    limit: int = Query(100, ge=1, le=500),
    user=Depends(get_current_user),
):
    """Estudiantes en riesgo académico: promedio<umbral O nota<umbral en materia del docente.
    Aplica factores de vulnerabilidad para priorizar."""
    if user.get("role") not in ("docente", "superadmin", "admin"):
        raise HTTPException(403, "Solo docentes")

    cedulas = await _cedulas_de_mis_grupos(user, codigo_grupo)
    if not cedulas:
        return {"items": [], "total": 0}

    # Compute average by student (only from historico_notas de mis grupos)
    if user.get("role") == "docente":
        docente_filter = {"docente_id": user["id"]}
    else:
        docente_filter = {}
    if codigo_grupo:
        docente_filter["codigo_grupo"] = codigo_grupo

    avg_pipe = [
        {"$match": {**docente_filter, "cedula": {"$in": list(cedulas)}}},
        {"$group": {
            "_id": "$cedula",
            "prom_grupo": {"$avg": "$nota"},
            "notas": {"$push": {"materia": "$asignatura_nombre", "nota": "$nota", "estado": "$estado", "periodo": "$periodo"}},
            "min_nota": {"$min": "$nota"},
            "max_nota": {"$max": "$nota"},
        }}
    ]
    avg_map = {}
    async for r in db.historico_notas.aggregate(avg_pipe):
        avg_map[r["_id"]] = r

    # Fetch students info
    students = await db.students.find(
        {"cedula": {"$in": list(cedulas)}},
        {"_id": 0, "cedula": 1, "nombre": 1, "apellidos": 1, "nombre_completo": 1,
         "correo": 1, "correo_institucional": 1, "telefono": 1,
         "programa": 1, "facultad": 1, "nivel": 1,
         "promedio": 1, "avance_pct": 1,
         "sisben_nivel": 1, "grupo_sisben": 1, "estrato": 1,
         "victima_conflicto": 1, "grupo_vulnerable": 1, "discapacidad_flag": 1,
         "tipo_ubicacion": 1, "ciudad_nombre": 1, "departamento": 1}
    ).to_list(20000)

    items = []
    for s in students:
        c = s["cedula"]
        agg_data = avg_map.get(c, {})
        prom_grupo = agg_data.get("prom_grupo") or 0
        prom_general = s.get("promedio") or 0
        min_nota = agg_data.get("min_nota") or 0

        # Criterio combinado: bajo en mi(s) materia(s) O bajo general
        en_riesgo = False
        motivos = []
        if prom_grupo > 0 and prom_grupo < umbral:
            en_riesgo = True
            motivos.append(f"promedio en mis materias: {prom_grupo:.2f}")
        if min_nota > 0 and min_nota < umbral:
            en_riesgo = True
            motivos.append(f"nota mínima: {min_nota:.2f}")
        if prom_general > 0 and prom_general < umbral:
            en_riesgo = True
            motivos.append(f"promedio general: {prom_general:.2f}")
        if not en_riesgo:
            continue

        # Score de riesgo (+ vulnerabilidad)
        score = 0
        if prom_grupo > 0 and prom_grupo < umbral: score += (umbral - prom_grupo) * 40
        if s.get("victima_conflicto"): score += 15; motivos.append("víctima conflicto")
        if s.get("grupo_vulnerable"): score += 10; motivos.append("grupo vulnerable")
        if s.get("discapacidad_flag"): score += 8; motivos.append("con discapacidad")
        if s.get("sisben_nivel", "").startswith(("A", "B")): score += 5; motivos.append(f"SISBEN {s['sisben_nivel']}")

        items.append({
            **s,
            "prom_grupo": round(prom_grupo, 2),
            "min_nota": round(min_nota, 2),
            "notas_detalle": agg_data.get("notas", [])[:5],
            "score_riesgo": round(score, 1),
            "motivos": motivos,
        })

    items.sort(key=lambda x: x["score_riesgo"], reverse=True)
    return {"items": items[:limit], "total": len(items)}


@router.get("/students")
async def my_students(
    codigo_grupo: Optional[str] = None,
    riesgo: Optional[bool] = None,
    user=Depends(get_current_user),
):
    """Lista de estudiantes del docente. Filtro opcional por grupo y riesgo."""
    if user.get("role") not in ("docente", "superadmin", "admin"):
        raise HTTPException(403, "Solo docentes")

    cedulas = await _cedulas_de_mis_grupos(user, codigo_grupo)
    if not cedulas:
        return {"students": [], "total": 0}

    match = {"cedula": {"$in": list(cedulas)}}
    if riesgo:
        match["promedio"] = {"$lt": 3.0, "$gt": 0}

    students = await db.students.find(
        match,
        {"_id": 0, "cedula": 1, "nombre": 1, "apellidos": 1, "nombre_completo": 1,
         "correo": 1, "correo_institucional": 1,
         "programa": 1, "facultad": 1, "nivel": 1, "promedio": 1, "avance_pct": 1,
         "sisben_nivel": 1, "estrato": 1,
         "grupo_vulnerable": 1, "victima_conflicto": 1, "discapacidad_flag": 1,
         "tipo_ubicacion": 1, "ciudad_nombre": 1, "departamento": 1}
    ).sort("promedio", 1).limit(500).to_list(500)
    total = await db.students.count_documents(match)
    return {"students": students, "total": total}
