"""Dashboards aggregation router."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from auth import get_current_user
from database import db
from scope import apply_role_scope
from academic_filter import academic_notes_match

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])


def _build_match(args: dict) -> dict:
    """Build MongoDB match dict from query params."""
    m = {}
    mapping = {
        "periodo": "periodo",
        "facultad": "facultad",
        "programa": "programa",
        "genero": "genero",
        "estrato": "estrato",
        "etnia": "etnia",
        "tipo_ubicacion": "tipo_ubicacion",
        "estado_matricula": "estado_matricula",
        "municipio_codigo": "ciudad_codigo",
    }
    for k, field in mapping.items():
        v = args.get(k)
        if v not in (None, "", "all", "todos"):
            m[field] = v
    # Booleans
    for k, field in {"sisben": "sisben_tiene", "discapacidad": "discapacidad_flag",
                     "victima": "victima_conflicto", "grupo_vulnerable": "grupo_vulnerable"}.items():
        v = args.get(k)
        if v in ("true", "1", True):
            m[field] = True
        elif v in ("false", "0", False):
            m[field] = False
    return m


async def _apply_docente_materia(match: dict, docente_id, materia_id, codigo_grupo=None) -> dict:
    """If docente_id/materia_id/codigo_grupo are present, restrict match to intersection
    of cédulas.

    - codigo_grupo: matriculados en ese grupo específico.
    - docente_id: SOLO matriculados actuales del docente (no incluye histórico de periodos anteriores
      para evitar sumar estudiantes de cursos que ya no dicta).
    - materia_id: cédulas con notas históricas en esa materia (útil para análisis por materia).
    """
    cedulas_sets = []
    if codigo_grupo and codigo_grupo not in ("all", "todos", ""):
        cedulas = await db.matriculas.distinct("cedula", {"codigo_grupo": codigo_grupo})
        cedulas_sets.append(set(cedulas))
    if docente_id and docente_id not in ("all", "todos", ""):
        # Solo matriculas activas del docente (periodo actual)
        c2 = set(await db.matriculas.distinct("cedula", {"docente_id": docente_id}))
        cedulas_sets.append(c2)
    if materia_id and materia_id not in ("all", "todos", ""):
        c = set(await db.historico_notas.distinct("cedula", {"materia_id": materia_id}))
        cedulas_sets.append(c)
    if cedulas_sets:
        final = cedulas_sets[0]
        for s in cedulas_sets[1:]:
            final = final & s
        match["cedula"] = {"$in": list(final)} if final else "__NO_MATCH__"
    return match


async def _common_params(
    periodo: Optional[str] = None,
    facultad: Optional[str] = None,
    programa: Optional[str] = None,
    genero: Optional[str] = None,
    estrato: Optional[str] = None,
    etnia: Optional[str] = None,
    tipo_ubicacion: Optional[str] = None,
    estado_matricula: Optional[str] = None,
    municipio_codigo: Optional[str] = None,
    sisben: Optional[str] = None,
    discapacidad: Optional[str] = None,
    victima: Optional[str] = None,
    grupo_vulnerable: Optional[str] = None,
    docente_id: Optional[str] = None,
    materia_id: Optional[str] = None,
    codigo_grupo: Optional[str] = None,
    user=Depends(get_current_user),
):
    match = _build_match(locals())
    match = await _apply_docente_materia(match, docente_id, materia_id, codigo_grupo)
    # Enforce role-based scope (decano/coordinador filter by facultad/programa)
    match = apply_role_scope(user, match)
    return match


@router.get("/executive")
async def executive(match: dict = Depends(_common_params), user=Depends(get_current_user)):
    coll = db.students
    pipeline = [{"$match": match}] if match else []
    total = await coll.count_documents(match)
    if not total:
        return {"kpis": {}, "by_program": [], "by_genero": [], "by_estrato": [], "by_ubicacion": []}

    agg_kpi = await coll.aggregate(pipeline + [
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "matriculados": {"$sum": {"$cond": [{"$eq": ["$estado_matricula", "Estudiante Matriculado"]}, 1, 0]}},
            "promedio": {"$avg": {"$cond": [{"$gt": ["$promedio", 0]}, "$promedio", None]}},
            "avance_pct": {"$avg": "$avance_pct"},
            "vulnerables": {"$sum": {"$cond": ["$grupo_vulnerable", 1, 0]}},
            "victimas": {"$sum": {"$cond": ["$victima_conflicto", 1, 0]}},
            "discapacidad": {"$sum": {"$cond": ["$discapacidad_flag", 1, 0]}},
            "rurales": {"$sum": {"$cond": [{"$in": ["$tipo_ubicacion", ["Rural", "Semirural"]]}, 1, 0]}},
        }}
    ]).to_list(1)

    # Notas per periodo from historico_notas (source of truth), EXCLUYENDO extensión + inglés fuera de malla
    if match:
        cedulas_match = await db.students.distinct("cedula", match)
        hn_match = {"cedula": {"$in": cedulas_match}}
    else:
        hn_match = {}
    hn_match = academic_notes_match(hn_match)
    notas_per_periodo = {}
    async for r in db.historico_notas.aggregate([
        {"$match": hn_match},
        {"$group": {"_id": "$periodo", "n": {"$sum": 1},
                    "prom": {"$avg": "$nota"},
                    "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}}}}
    ]):
        p = r["_id"]
        notas_per_periodo[p] = {
            "n": r["n"], "prom": round(r["prom"] or 0, 2),
            "aprob_pct": round((r["aprob"] / r["n"] * 100) if r["n"] else 0, 1),
        }

    by_program = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$programa", "n": {"$sum": 1},
                    "prom": {"$avg": {"$cond": [{"$gt": ["$promedio", 0]}, "$promedio", None]}}}},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "programa": "$_id", "n": 1, "prom": {"$round": [{"$ifNull": ["$prom", 0]}, 2]}}}
    ]).to_list(100)

    by_genero = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$genero", "n": {"$sum": 1}}},
        {"$project": {"_id": 0, "genero": "$_id", "n": 1}}
    ]).to_list(10)

    by_estrato = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$estrato", "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "estrato": "$_id", "n": 1}}
    ]).to_list(20)

    by_ubicacion = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$tipo_ubicacion", "n": {"$sum": 1}}},
        {"$project": {"_id": 0, "tipo": "$_id", "n": 1}}
    ]).to_list(10)

    by_edad = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$grupo_etario", "n": {"$sum": 1}}},
        {"$project": {"_id": 0, "rango": "$_id", "n": 1}}
    ]).to_list(10)
    # Orden cronológico de grupos etarios
    _ORDEN = {"Adolescencia": 1, "Juventud": 2, "Adultez joven": 3, "Adultez media": 4, "Persona mayor": 5, "Sin dato": 6}
    by_edad.sort(key=lambda x: _ORDEN.get(x.get("rango", ""), 99))

    by_rango_edad = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$rango_edad", "n": {"$sum": 1}}},
        {"$project": {"_id": 0, "rango": "$_id", "n": 1}}
    ]).to_list(15)
    _ORDEN_R = {"Menor 18": 1, "18-22": 2, "23-27": 3, "28-32": 4, "33-40": 5, "41-50": 6, "51+": 7}
    by_rango_edad.sort(key=lambda x: _ORDEN_R.get(x.get("rango", ""), 99))

    by_vulnerabilidad = await coll.aggregate(pipeline + [
        {"$match": {"grupo_vulnerable": True}},
        {"$group": {"_id": "$tipo_grupo_vulnerable", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$limit": 10},
        {"$project": {"_id": 0, "tipo": "$_id", "n": 1}}
    ]).to_list(15)

    by_pais = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$pais", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$limit": 15},
        {"$project": {"_id": 0, "pais": "$_id", "n": 1}}
    ]).to_list(15)

    by_departamento = await coll.aggregate(pipeline + [
        {"$match": {"departamento": {"$nin": [None, "", "Sin Dato", "Sin dato"]}}},
        {"$group": {"_id": "$departamento", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$limit": 15},
        {"$project": {"_id": 0, "departamento": "$_id", "n": 1}}
    ]).to_list(15)

    total_programas = len(await coll.distinct("programa", match))
    total_facultades = len(await coll.distinct("facultad", match))

    # Promedio general PONDERADO desde historico_notas (nota real, no promedio de promedios)
    # EXCLUYE cursos de extensión + inglés fuera de malla
    prom_ponderado = 0
    if not match or match.get("cedula", {}).get("$in") is not None or not match:
        hn_match_general = academic_notes_match(hn_match if match else {})
        rr = await db.historico_notas.aggregate([
            {"$match": hn_match_general},
            {"$group": {"_id": None, "p": {"$avg": "$nota"}}}
        ]).to_list(1)
        if rr:
            prom_ponderado = round(rr[0]["p"] or 0, 2)

    k = agg_kpi[0] if agg_kpi else {}
    return {
        "kpis": {
            "total": k.get("total", 0),
            "matriculados": k.get("matriculados", 0),
            "programas": total_programas,
            "facultades": total_facultades,
            "promedio": prom_ponderado or round(k.get("promedio", 0) or 0, 2),
            "avance_pct": round(k.get("avance_pct", 0) or 0, 1),
            "vulnerables": k.get("vulnerables", 0),
            "victimas": k.get("victimas", 0),
            "discapacidad": k.get("discapacidad", 0),
            "rurales": k.get("rurales", 0),
            "promedio_2025_2": (notas_per_periodo.get("2025-2") or {}).get("prom", 0),
            "promedio_2026_1": (notas_per_periodo.get("2026-1") or {}).get("prom", 0),
            "notas_2025_2": (notas_per_periodo.get("2025-2") or {}).get("n", 0),
            "notas_2026_1": (notas_per_periodo.get("2026-1") or {}).get("n", 0),
            "aprob_pct_2025_2": (notas_per_periodo.get("2025-2") or {}).get("aprob_pct", 0),
            "aprob_pct_2026_1": (notas_per_periodo.get("2026-1") or {}).get("aprob_pct", 0),
        },
        "by_program": by_program,
        "by_genero": by_genero,
        "by_estrato": by_estrato,
        "by_ubicacion": by_ubicacion,
        "by_edad": by_edad,
        "by_rango_edad": by_rango_edad,
        "by_vulnerabilidad": by_vulnerabilidad,
        "by_pais": by_pais,
        "by_departamento": by_departamento,
    }


@router.get("/academic")
async def academic(
    include_extension: bool = False,
    match: dict = Depends(_common_params),
    user=Depends(get_current_user),
):
    """Dashboard académico basado 100% en historico_notas (2 periodos reales: 2025-2 y 2026-1)
    + campo 'nivel' (semestre) del estudiante para trayectoria 2026-2.

    Por defecto EXCLUYE las notas del área EXTENSION (cursos/diplomados).
    Con `?include_extension=true` se incluyen.
    """
    coll = db.students
    pipeline = [{"$match": match}] if match else []

    # Restringir historico_notas a las cédulas del match global
    hn_base = {}
    if match:
        cedulas_match = await db.students.distinct("cedula", match)
        hn_base["cedula"] = {"$in": cedulas_match}
    if not include_extension:
        # Excluir cursos de Extensión Académica + Inglés Fuera de la Malla + Diplomados
        # usando el helper unificado (codigo_asignatura EXT* + programa marcadores)
        hn_base = academic_notes_match(hn_base)

    # ============================================================
    # SECCIÓN 1 · Comparativo por periodo
    # ============================================================
    # 1a) Estados de notas por periodo (barras apiladas)
    estados_por_periodo = {}
    async for r in db.historico_notas.aggregate([
        {"$match": hn_base},
        {"$group": {"_id": {"p": "$periodo", "e": "$estado"}, "n": {"$sum": 1}}},
    ]):
        per = r["_id"]["p"]
        est = r["_id"]["e"] or "Sin dato"
        estados_por_periodo.setdefault(per, {})[est] = r["n"]
    estados_periodo = []
    for per in sorted(estados_por_periodo.keys()):
        row = {"periodo": per, **estados_por_periodo[per]}
        row["total"] = sum(estados_por_periodo[per].values())
        estados_periodo.append(row)

    # 1b) Distribución de notas por rangos (0-1, 1-2, 2-3, 3-4, 4-5) para AMBOS periodos
    distribucion_notas = {}
    async for r in db.historico_notas.aggregate([
        {"$match": hn_base},
        {"$bucket": {
            "groupBy": "$nota",
            "boundaries": [0, 1, 2, 3, 3.5, 4, 4.5, 5.01],
            "default": "Otros",
            "output": {"n": {"$sum": 1}, "por_periodo": {"$push": "$periodo"}}
        }}
    ]):
        low = r["_id"] if r["_id"] != "Otros" else None
        labels = {0: "0.0–1.0", 1: "1.0–2.0", 2: "2.0–3.0", 3: "3.0–3.5", 3.5: "3.5–4.0", 4: "4.0–4.5", 4.5: "4.5–5.0"}
        label = labels.get(low, str(low))
        p25 = sum(1 for p in r["por_periodo"] if p == "2025-2")
        p26 = sum(1 for p in r["por_periodo"] if p == "2026-1")
        distribucion_notas[label] = {"rango": label, "total": r["n"], "p_2025_2": p25, "p_2026_1": p26}
    distribucion = [distribucion_notas[k] for k in sorted(distribucion_notas.keys(), key=lambda x: x)]

    # 1c) Promedio + % aprobación por bloque × periodo
    bloque_periodo = []
    async for r in db.historico_notas.aggregate([
        {"$match": {**hn_base, "bloque": {"$nin": [None, ""]}}},
        {"$group": {"_id": {"b": "$bloque", "p": "$periodo"},
                    "n": {"$sum": 1},
                    "prom": {"$avg": "$nota"},
                    "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}}}},
        {"$sort": {"_id.p": 1, "_id.b": 1}},
    ]):
        bloque_periodo.append({
            "bloque": r["_id"]["b"], "periodo": r["_id"]["p"],
            "n": r["n"], "prom": round(r["prom"] or 0, 2),
            "aprob_pct": round((r["aprob"] / r["n"] * 100) if r["n"] else 0, 1),
        })

    # ============================================================
    # SECCIÓN 2 · Rendimiento por materia y facultad
    # ============================================================
    # 2a) Top 10 asignaturas con MÁS REPROBACIÓN (últimos 2 periodos)
    top_reprobadas = await db.historico_notas.aggregate([
        {"$match": {**hn_base, "asignatura_nombre": {"$nin": [None, ""]}}},
        {"$group": {
            "_id": "$asignatura_nombre",
            "n": {"$sum": 1},
            "prom": {"$avg": "$nota"},
            "reprob": {"$sum": {"$cond": [{"$eq": ["$estado", "Reprobada"]}, 1, 0]}},
            "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
        }},
        {"$match": {"n": {"$gte": 30}}},  # solo materias con muestra significativa
        {"$project": {"_id": 0, "asignatura": "$_id", "n": 1, "reprob": 1,
                      "prom": {"$round": ["$prom", 2]},
                      "pct_reprob": {"$round": [{"$multiply": [{"$divide": ["$reprob", "$n"]}, 100]}, 1]}}},
        {"$sort": {"pct_reprob": -1}},
        {"$limit": 10},
    ]).to_list(10)

    # 2b) Top 10 asignaturas con MEJOR rendimiento
    top_aprobadas = await db.historico_notas.aggregate([
        {"$match": {**hn_base, "asignatura_nombre": {"$nin": [None, ""]}}},
        {"$group": {
            "_id": "$asignatura_nombre",
            "n": {"$sum": 1}, "prom": {"$avg": "$nota"},
            "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
        }},
        {"$match": {"n": {"$gte": 30}}},
        {"$project": {"_id": 0, "asignatura": "$_id", "n": 1,
                      "prom": {"$round": ["$prom", 2]},
                      "pct_aprob": {"$round": [{"$multiply": [{"$divide": ["$aprob", "$n"]}, 100]}, 1]}}},
        {"$sort": {"prom": -1}},
        {"$limit": 10},
    ]).to_list(10)

    # 2c) Facultad de la asignatura — DEPRECATED (dato anormal, no confiable)
    by_area = []

    # 2d) Promedio por PROGRAMA — segmentado en 3 categorías:
    #     REGULAR (pregrados, tecnologías, especializaciones, convenios)
    #     INGLÉS (cursos de inglés fuera de la malla)
    #     EXTENSIÓN (cursos y diplomados)
    def _cat(nombre):
        if not nombre:
            return "regular"
        u = nombre.upper()
        if "INGLÉS" in u or "INGLES" in u:
            return "ingles"
        if u.startswith("CURSO ") or u.startswith("DIPLOMADO ") or u.startswith("DPLOMADO ") or u.startswith("DIPOMADO ") or "HERRAMIENTAS BÁSICAS" in u or "TRABAJO EN LINEA" in u or "TRABAJO EN LÍNEA" in u:
            return "extension"
        return "regular"

    prog_raw = await db.historico_notas.aggregate([
        {"$match": {**hn_base, "programa": {"$nin": [None, ""]}}},
        {"$group": {
            "_id": "$programa", "n": {"$sum": 1},
            "prom": {"$avg": "$nota"},
            "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
            "prom_2025_2": {"$avg": {"$cond": [{"$eq": ["$periodo", "2025-2"]}, "$nota", None]}},
            "prom_2026_1": {"$avg": {"$cond": [{"$eq": ["$periodo", "2026-1"]}, "$nota", None]}},
        }},
        {"$project": {"_id": 0, "programa": "$_id", "n": 1,
                      "prom": {"$round": [{"$ifNull": ["$prom", 0]}, 2]},
                      "prom_2025_2": {"$round": [{"$ifNull": ["$prom_2025_2", 0]}, 2]},
                      "prom_2026_1": {"$round": [{"$ifNull": ["$prom_2026_1", 0]}, 2]},
                      "pct_aprob": {"$round": [{"$multiply": [{"$divide": ["$aprob", "$n"]}, 100]}, 1]}}},
        {"$sort": {"n": -1}},
    ]).to_list(500)

    by_program_regular, by_program_ingles, by_program_extension = [], [], []
    for p in prog_raw:
        cat = _cat(p["programa"])
        if cat == "ingles":
            by_program_ingles.append(p)
        elif cat == "extension":
            by_program_extension.append(p)
        else:
            by_program_regular.append(p)

    # Compat: by_program_avg = regular únicamente (para no romper otros consumidores)
    by_program_avg = by_program_regular

    # ============================================================
    # SECCIÓN 3 · Trayectoria estudiantil (nivel 2026-2)
    # ============================================================
    # 3a) Estudiantes por nivel/semestre
    by_nivel = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$nivel", "n": {"$sum": 1},
                    "prom": {"$avg": {"$cond": [{"$gt": ["$promedio", 0]}, "$promedio", None]}}}},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "nivel": "$_id", "n": 1,
                      "prom": {"$round": [{"$ifNull": ["$prom", 0]}, 2]}}}
    ]).to_list(15)

    # 3b) Créditos aprobados vs reprobados por periodo
    creditos = []
    async for r in db.historico_notas.aggregate([
        {"$match": hn_base},
        {"$group": {"_id": "$periodo",
                    "cred_aprob": {"$sum": {"$cond": ["$aprobada", "$creditos", 0]}},
                    "cred_reprob": {"$sum": {"$cond": [{"$eq": ["$estado", "Reprobada"]}, "$creditos", 0]}},
                    "cred_cancel": {"$sum": {"$cond": [{"$eq": ["$estado", "Cancelada"]}, "$creditos", 0]}}}},
        {"$sort": {"_id": 1}},
    ]):
        creditos.append({
            "periodo": r["_id"],
            "aprobados": r["cred_aprob"] or 0,
            "reprobados": r["cred_reprob"] or 0,
            "cancelados": r["cred_cancel"] or 0,
        })

    # 3c) Habilitaciones: total y % éxito por periodo
    habilitaciones = []
    async for r in db.historico_notas.aggregate([
        {"$match": {**hn_base, "estado": {"$regex": "^Habilitada", "$options": "i"}}},
        {"$group": {"_id": "$periodo",
                    "total": {"$sum": 1},
                    "exito": {"$sum": {"$cond": [{"$eq": ["$estado", "Habilitada-Aprobada"]}, 1, 0]}}}},
        {"$sort": {"_id": 1}},
    ]):
        habilitaciones.append({
            "periodo": r["_id"],
            "total": r["total"],
            "exito": r["exito"],
            "pct_exito": round((r["exito"] / r["total"] * 100) if r["total"] else 0, 1),
        })

    # 3d) Avance curricular por programa
    avance = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$programa", "avance": {"$avg": "$avance_pct"}, "n": {"$sum": 1}}},
        {"$sort": {"avance": -1}},
        {"$project": {"_id": 0, "programa": "$_id", "avance": {"$round": ["$avance", 1]}, "n": 1}}
    ]).to_list(25)

    # ============================================================
    # KPIs generales
    # ============================================================
    en_riesgo = await coll.count_documents({**match, "promedio": {"$lt": 3.0, "$gt": 0}})
    excelencia = await coll.count_documents({**match, "promedio": {"$gte": 4.5}})

    # Tasa aprobación global (aprobadas / total notas evaluadas — excluye canceladas/prematriculadas/homologadas)
    global_stats = await db.historico_notas.aggregate([
        {"$match": {**hn_base, "estado": {"$in": ["Aprobada", "Reprobada", "Habilitada-Aprobada", "Habilitada-Reprobada"]}}},
        {"$group": {"_id": None,
                    "total": {"$sum": 1},
                    "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
                    "prom": {"$avg": "$nota"}}},
    ]).to_list(1)
    gs = global_stats[0] if global_stats else {"total": 0, "aprob": 0, "prom": 0}
    tasa_aprob = round((gs["aprob"] / gs["total"] * 100) if gs["total"] else 0, 1)

    # Habilitaciones agregadas
    total_hab = sum(h["total"] for h in habilitaciones)
    total_hab_exito = sum(h["exito"] for h in habilitaciones)
    tasa_hab = round((total_hab_exito / total_hab * 100) if total_hab else 0, 1)

    return {
        "kpis": {
            "en_riesgo": en_riesgo,
            "excelencia": excelencia,
            "tasa_aprob_global": tasa_aprob,
            "notas_evaluadas": gs["total"],
            "tasa_habilitacion_exito": tasa_hab,
            "total_habilitaciones": total_hab,
            "promedio_global": round(gs["prom"] or 0, 2),
        },
        "estados_por_periodo": estados_periodo,
        "distribucion_notas": distribucion,
        "bloque_periodo": bloque_periodo,
        "top_reprobadas": top_reprobadas,
        "top_aprobadas": top_aprobadas,
        "by_area": by_area,
        "by_program_avg": by_program_avg,
        "by_program_regular": by_program_regular,
        "by_program_ingles": by_program_ingles,
        "by_program_extension": by_program_extension,
        "by_nivel": by_nivel,
        "creditos": creditos,
        "habilitaciones": habilitaciones,
        "avance": avance,
        # Compatibilidad
        "en_riesgo": en_riesgo,
        "excelencia": excelencia,
        "by_facultad": by_area,
    }


@router.get("/territorial")
async def territorial(match: dict = Depends(_common_params), user=Depends(get_current_user)):
    coll = db.students
    pipeline = [{"$match": match}] if match else []

    municipios = await coll.aggregate(pipeline + [
        {"$group": {
            "_id": {"codigo": "$ciudad_codigo", "nombre": "$ciudad_nombre",
                    "lat": "$lat", "lon": "$lon", "departamento": "$departamento",
                    "pais": "$pais"},
            "n": {"$sum": 1},
            "prom": {"$avg": "$promedio"},
            "vulnerables": {"$sum": {"$cond": ["$grupo_vulnerable", 1, 0]}},
            "rural": {"$sum": {"$cond": [{"$in": ["$tipo_ubicacion", ["Rural", "Semirural"]]}, 1, 0]}},
        }},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "codigo": "$_id.codigo", "nombre": "$_id.nombre",
                      "lat": "$_id.lat", "lon": "$_id.lon",
                      "departamento": "$_id.departamento",
                      "pais": "$_id.pais",
                      "n": 1, "prom": {"$round": ["$prom", 2]},
                      "vulnerables": 1, "rural": 1}}
    ]).to_list(3000)

    por_departamento = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$departamento", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "departamento": {"$ifNull": ["$_id", "Sin dato"]}, "n": 1}}
    ]).to_list(100)

    por_pais = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$pais", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "pais": {"$ifNull": ["$_id", "Sin dato"]}, "n": 1}}
    ]).to_list(50)

    # Resumen de cobertura territorial (totales y cuántos sin dato)
    match_query = match if match else {}
    total = await coll.count_documents(match_query)
    con_georef = await coll.count_documents({**match_query, "lat": {"$ne": 0}})
    sin_georef = total - con_georef
    sin_ciudad = await coll.count_documents({**match_query, "$or": [{"ciudad_nombre": "Sin dato"}, {"ciudad_nombre": ""}, {"ciudad_nombre": None}]})
    sin_departamento = await coll.count_documents({**match_query, "$or": [{"departamento": "Sin dato"}, {"departamento": ""}, {"departamento": None}]})
    sin_pais = await coll.count_documents({**match_query, "$or": [{"pais": "Sin dato"}, {"pais": ""}, {"pais": None}]})
    resumen = {
        "total": total,
        "con_georef": con_georef,
        "sin_georef": sin_georef,
        "sin_ciudad": sin_ciudad,
        "sin_departamento": sin_departamento,
        "sin_pais": sin_pais,
        "n_municipios": len(set((m["nombre"], m["departamento"]) for m in municipios if m.get("nombre") and m["nombre"] != "Sin dato")),
        "n_departamentos": len([d for d in por_departamento if d["departamento"] != "Sin dato"]),
        "n_paises": len([p for p in por_pais if p["pais"] != "Sin dato"]),
    }

    return {
        "municipios": municipios,
        "por_departamento": por_departamento,
        "por_pais": por_pais,
        "resumen": resumen,
    }


@router.get("/historical")
async def historical(programa: Optional[str] = None, user=Depends(get_current_user)):
    """Histórico académico. Solo periodos con notas reales cargadas (2025-2 y 2026-1).
    Deriva TODO desde historico_notas (nota, aprobada, programa) y matriculas para el
    conteo de matriculados únicos por periodo. EXCLUYE cursos de extensión + inglés fuera de malla."""
    hn_match = {}
    if programa:
        hn_match["programa"] = programa
    hn_match = academic_notes_match(hn_match)

    # ---- Series por periodo (promedio ponderado + tasa aprobación + matriculados únicos)
    series_periodo = []
    async for r in db.historico_notas.aggregate([
        {"$match": hn_match},
        {"$group": {
            "_id": "$periodo",
            "prom": {"$avg": "$nota"},
            "n_notas": {"$sum": 1},
            "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
            "cedulas": {"$addToSet": "$cedula"},
        }},
        {"$project": {
            "_id": 0, "periodo": "$_id",
            "promedio": {"$round": [{"$ifNull": ["$prom", 0]}, 2]},
            "tasa_aprobacion": {"$round": [{"$multiply": [{"$divide": ["$aprob", "$n_notas"]}, 100]}, 1]},
            "matriculados": {"$size": "$cedulas"},
            "n_notas": 1,
        }},
        {"$sort": {"periodo": 1}},
    ]):
        series_periodo.append(r)

    # ---- Por programa × periodo (para comparativo detallado)
    # hn_match ya incluye academic_notes_match; agregar filtro de programa no nulo
    by_program_match = dict(hn_match)
    programa_extra = {"programa": {"$nin": [None, ""]}}
    if "$and" in by_program_match:
        by_program_match["$and"] = list(by_program_match["$and"]) + [programa_extra]
    else:
        by_program_match.update(programa_extra)
    by_program = []
    async for r in db.historico_notas.aggregate([
        {"$match": by_program_match},
        {"$group": {
            "_id": {"prog": "$programa", "per": "$periodo"},
            "prom": {"$avg": "$nota"},
            "n_notas": {"$sum": 1},
            "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
            "cedulas": {"$addToSet": "$cedula"},
        }},
        {"$project": {
            "_id": 0,
            "programa": "$_id.prog",
            "periodo": "$_id.per",
            "promedio": {"$round": [{"$ifNull": ["$prom", 0]}, 2]},
            "tasa_aprobacion": {"$round": [{"$multiply": [{"$divide": ["$aprob", "$n_notas"]}, 100]}, 1]},
            "matriculados": {"$size": "$cedulas"},
            "n_notas": 1,
        }},
        {"$sort": {"programa": 1, "periodo": 1}},
    ]):
        by_program.append(r)

    return {"by_program": by_program, "series_periodo": series_periodo}


@router.get("/filters")
async def filter_options(user=Depends(get_current_user)):
    """Return available filter values from the data. Includes facultad→programa map for cascading filters."""
    def _clean(values, invalid=None):
        invalid = invalid or {"SELECCIONE...", "SELECCIONE", "NO REGISTRA", ""}
        return sorted([v for v in values if v and str(v).strip().upper() not in invalid])

    # Apply role scope to base match for all distinct queries
    base_match = apply_role_scope(user, {})
    if "_no_scope_" in base_match:
        return {"programas": [], "facultades": [], "periodos": [], "generos": [], "estratos": [],
                "etnias": [], "ubicaciones": [], "estados_matricula": [], "facultad_programa": {},
                "docentes": [], "materias": [], "grupos": []}

    programas = _clean(await db.students.distinct("programa", base_match))
    facultades = _clean(await db.students.distinct("facultad", base_match))
    periodos = sorted([p for p in await db.students.distinct("periodo", base_match) if p])
    generos = _clean(await db.students.distinct("genero", base_match))
    estratos = _clean(await db.students.distinct("estrato", base_match))
    etnias = _clean(await db.students.distinct("etnia", base_match))
    ubicaciones = _clean(await db.students.distinct("tipo_ubicacion", base_match))
    estados_matricula = _clean(await db.students.distinct("estado_matricula", base_match))

    # facultad -> [programas] mapping for cascading filters
    pipe = [
        {"$match": {**base_match, "facultad": {"$ne": None}, "programa": {"$ne": None}}},
        {"$group": {"_id": {"f": "$facultad", "p": "$programa"}}},
    ]
    facultad_programa = {}
    async for r in db.students.aggregate(pipe):
        f = r["_id"].get("f"); p = r["_id"].get("p")
        if not f or not p:
            continue
        facultad_programa.setdefault(f, set()).add(p)
    facultad_programa = {k: sorted(v) for k, v in facultad_programa.items()}

    # Docentes y materias para filtros globales
    docentes_rows = await db.users.find({"role": "profesor"}, {"_id": 0, "id": 1, "full_name": 1, "email": 1}).to_list(1000)
    docentes = sorted([{"id": d["id"], "nombre": d.get("full_name") or d.get("email", "")} for d in docentes_rows], key=lambda x: x["nombre"])

    materias_rows = await db.materias.find({}, {"_id": 0, "id": 1, "nombre": 1, "codigo": 1}).to_list(5000)
    materias = sorted(
        [{"id": m["id"], "nombre": m.get("nombre", ""), "codigo": m.get("codigo", "")} for m in materias_rows],
        key=lambda x: x["nombre"],
    )

    # Grupos activos (limitados a los 200 más relevantes o filtrados por rol)
    grupos_query = {}
    if user.get("role") == "profesor":
        grupos_query = {"docente_id": user["id"]}
    elif user.get("role") in ("decano", "coordinador"):
        # scoping via cedulas → codigos_grupo
        cedulas_scope = await db.students.distinct("cedula", base_match)
        if cedulas_scope:
            codigos = await db.matriculas.distinct("codigo_grupo", {"cedula": {"$in": cedulas_scope}})
            grupos_query = {"codigo_grupo": {"$in": codigos}} if codigos else {"codigo_grupo": "__NONE__"}
        else:
            grupos_query = {"codigo_grupo": "__NONE__"}
    grupos_rows = await db.grupos.find(grupos_query, {
        "_id": 0, "codigo_grupo": 1, "asignatura_nombre": 1,
        "asignatura_codigo": 1,
        "programa": 1, "docente_nombre": 1, "docente_id": 1, "periodo": 1,
        "dia": 1, "hora": 1,
    }).sort("codigo_grupo", 1).to_list(2000)
    grupos = [
        {"id": g["codigo_grupo"],
         "nombre": f"{g.get('asignatura_nombre', '')[:35]}",
         "codigo": g["codigo_grupo"],
         "asignatura_codigo": g.get("asignatura_codigo", ""),
         "programa": g.get("programa", "")[:30],
         "docente": g.get("docente_nombre", ""),
         "docente_id": g.get("docente_id", ""),
         "periodo": g.get("periodo", ""),
         "dia": g.get("dia", ""),
         "hora": g.get("hora", "")}
        for g in grupos_rows
    ]

    return {
        "programas": programas,
        "facultades": facultades,
        "periodos": periodos,
        "generos": generos,
        "estratos": estratos,
        "etnias": etnias,
        "ubicaciones": ubicaciones,
        "estados_matricula": estados_matricula,
        "facultad_programa": facultad_programa,
        "docentes": docentes,
        "materias": materias,
        "grupos": grupos,
    }
