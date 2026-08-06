"""Docente dashboard v2 — restringido a sus grupos asignados con panel de riesgo académico."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from auth import get_current_user
from database import db
from scope import apply_role_scope
from academic_filter import academic_notes_match

router = APIRouter(prefix="/api/dashboards/docente", tags=["dashboards-docente"])


ALLOWED_ROLES = ("profesor", "superadmin", "direccion", "decano", "coordinador")


async def _my_groups(user):
    """Return groups visible to this user:
    - superadmin/direccion: all
    - profesor: only where docente_id matches
    - decano/coordinador: groups whose students are in scope (may be many)
    """
    role = user.get("role")
    if role in ("superadmin", "direccion"):
        return await db.grupos.find({}, {"_id": 0}).to_list(5000)
    if role == "profesor":
        return await db.grupos.find({"docente_id": user["id"]}, {"_id": 0}).to_list(1000)
    if role in ("decano", "coordinador"):
        # Find cedulas in scope, then grupos where those cedulas are matriculated
        scope_match = apply_role_scope(user, {})
        if "_no_scope_" in scope_match:
            return []
        cedulas = await db.students.distinct("cedula", scope_match)
        if not cedulas:
            return []
        codigos = await db.matriculas.distinct("codigo_grupo", {"cedula": {"$in": cedulas}})
        if not codigos:
            return []
        return await db.grupos.find({"codigo_grupo": {"$in": codigos}}, {"_id": 0}).to_list(2000)
    return []


async def _cedulas_de_mis_grupos(user, codigo_grupo: Optional[str] = None):
    """Cédulas visibles al usuario. Aplica scope de rol."""
    role = user.get("role")
    if codigo_grupo:
        # Validate access to the specific group
        groups = await _my_groups(user)
        codigos = [g["codigo_grupo"] for g in groups]
        if codigo_grupo not in codigos and role not in ("superadmin", "direccion"):
            raise HTTPException(403, "No tienes acceso a este grupo")
        cedulas = await db.matriculas.distinct("cedula", {"codigo_grupo": codigo_grupo})
        return set(cedulas)
    # No codigo_grupo: return all cedulas in scope
    if role in ("superadmin", "direccion"):
        return set(await db.students.distinct("cedula", {}))
    if role == "profesor":
        groups = await _my_groups(user)
        codigos = [g["codigo_grupo"] for g in groups]
        if not codigos:
            return set()
        return set(await db.matriculas.distinct("cedula", {"codigo_grupo": {"$in": codigos}}))
    if role in ("decano", "coordinador"):
        scope_match = apply_role_scope(user, {})
        if "_no_scope_" in scope_match:
            return set()
        return set(await db.students.distinct("cedula", scope_match))
    return set()


@router.get("/me")
async def my_overview(codigo_grupo: Optional[str] = None, user=Depends(get_current_user)):
    if user.get("role") not in ALLOWED_ROLES:
        raise HTTPException(403, "Rol no autorizado para este panel")

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
    if user.get("role") not in ALLOWED_ROLES:
        raise HTTPException(403, "Solo docentes")

    cedulas = await _cedulas_de_mis_grupos(user, codigo_grupo)
    if not cedulas:
        return {"items": [], "total": 0}

    # Compute average by student (only from historico_notas de mis grupos)
    if user.get("role") == "profesor":
        docente_filter = {"docente_id": user["id"]}
    else:
        docente_filter = {}
    if codigo_grupo:
        docente_filter["codigo_grupo"] = codigo_grupo

    avg_pipe = [
        {"$match": academic_notes_match({**docente_filter, "cedula": {"$in": list(cedulas)}})},
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
    if user.get("role") not in ALLOWED_ROLES:
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



@router.get("/estudiante/{cedula}/historico")
async def estudiante_historico(cedula: str, user=Depends(get_current_user)):
    """Histórico académico completo del estudiante: todas sus notas + info personal.
    Docente solo puede ver estudiantes de sus grupos."""
    # Validar permiso docente
    if user.get("role") == "profesor":
        cedulas_permitidas = await _cedulas_de_mis_grupos(user)
        if cedula not in cedulas_permitidas:
            raise HTTPException(403, "No tienes acceso a este estudiante")

    est = await db.students.find_one({"cedula": cedula}, {"_id": 0})
    if not est:
        raise HTTPException(404, "Estudiante no encontrado")

    notas = await db.historico_notas.find(
        academic_notes_match({"cedula": cedula}),
        {"_id": 0, "id": 0, "created_at": 0}
    ).sort([("periodo", -1), ("asignatura_nombre", 1)]).to_list(500)

    # Agrupar por periodo con promedio
    from collections import defaultdict
    by_periodo = defaultdict(lambda: {"notas": [], "sum": 0, "count": 0, "aprob": 0, "repro": 0})
    for n in notas:
        p = n.get("periodo", "sin-periodo")
        by_periodo[p]["notas"].append(n)
        by_periodo[p]["sum"] += n.get("nota", 0)
        by_periodo[p]["count"] += 1
        if n.get("aprobada"):
            by_periodo[p]["aprob"] += 1
        elif n.get("nota", 0) > 0 and n.get("nota", 0) < 3.0:
            by_periodo[p]["repro"] += 1

    periodos = []
    for p in sorted(by_periodo.keys(), reverse=True):
        d = by_periodo[p]
        periodos.append({
            "periodo": p,
            "notas": d["notas"],
            "promedio": round(d["sum"] / d["count"], 2) if d["count"] else 0,
            "total": d["count"],
            "aprobadas": d["aprob"],
            "reprobadas": d["repro"],
        })

    return {
        "estudiante": est,
        "periodos": periodos,
        "total_notas": len(notas),
    }


@router.get("/grupos-comparativa")
async def grupos_comparativa(user=Depends(get_current_user)):
    """Comparativa por grupo: promedios en los últimos 2 periodos.
    Match cross-periodo por (docente_id + codigo_asignatura) porque codigo_grupo cambia cada periodo."""
    if user.get("role") not in ALLOWED_ROLES:
        raise HTTPException(403, "Solo docentes")

    groups = await _my_groups(user)
    if not groups:
        return {"grupos": []}

    # For each group, look up notas with matching docente_id + codigo_asignatura in the last 2 periodos
    # EXCLUYE cursos de extensión + inglés fuera de malla
    pipe = [
        {"$match": academic_notes_match({"docente_id": {"$ne": None}, "codigo_asignatura": {"$ne": ""}})},
        {"$group": {
            "_id": {
                "docente_id": "$docente_id",
                "asignatura": "$codigo_asignatura",
                "periodo": "$periodo",
            },
            "prom": {"$avg": "$nota"},
            "n": {"$sum": 1},
            "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
            "repro": {"$sum": {"$cond": [{"$and": [{"$lt": ["$nota", 3.0]}, {"$gt": ["$nota", 0]}]}, 1, 0]}},
        }},
    ]

    # Build (docente_id, asignatura) → { periodo: stats }
    by_key = {}
    async for r in db.historico_notas.aggregate(pipe):
        key = (r["_id"]["docente_id"], r["_id"]["asignatura"])
        by_key.setdefault(key, {})[r["_id"]["periodo"]] = r

    # Sort periodos globally to know last 2
    all_periodos = sorted({p for d in by_key.values() for p in d.keys()}, reverse=True)
    last_two = all_periodos[:2]

    out = []
    for g in groups:
        key = (g.get("docente_id"), g.get("asignatura_codigo"))
        stats = by_key.get(key, {})
        periodos_data = []
        for per in last_two:
            r = stats.get(per)
            if r:
                periodos_data.append({
                    "periodo": per,
                    "promedio": round(r["prom"] or 0, 2),
                    "total": r["n"],
                    "aprobadas": r["aprob"],
                    "reprobadas": r["repro"],
                    "tasa_aprobacion": round((r["aprob"] / r["n"] * 100) if r["n"] else 0, 1),
                })
        # Fallback: si no hay ningún histórico, incluye grupo con periodo actual y sin datos
        prom_last = periodos_data[0]["promedio"] if len(periodos_data) >= 1 else None
        prom_prev = periodos_data[1]["promedio"] if len(periodos_data) >= 2 else None
        variacion = round(prom_last - prom_prev, 2) if (prom_last is not None and prom_prev is not None) else None

        out.append({
            "codigo_grupo": g.get("codigo_grupo"),
            "asignatura_nombre": g.get("asignatura_nombre", ""),
            "asignatura_codigo": g.get("asignatura_codigo", ""),
            "programa": g.get("programa", ""),
            "docente_nombre": g.get("docente_nombre", ""),
            "periodo_grupo": g.get("periodo", ""),
            "periodos": periodos_data,
            "promedio_actual": prom_last,
            "promedio_anterior": prom_prev,
            "variacion": variacion,
            "tendencia": "sube" if variacion and variacion > 0.1 else "baja" if variacion and variacion < -0.1 else "estable",
        })

    # Sort: those with lowest averages first
    out.sort(key=lambda x: x["promedio_actual"] if x["promedio_actual"] is not None else 99)
    return {"grupos": out}
