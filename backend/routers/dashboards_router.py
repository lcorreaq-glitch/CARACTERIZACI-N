"""Dashboards aggregation router."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from auth import get_current_user
from database import db

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


def _common_params(
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
):
    return _build_match(locals())


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
            "promedio": {"$avg": "$promedio"},
            "avance_pct": {"$avg": "$avance_pct"},
            "vulnerables": {"$sum": {"$cond": ["$grupo_vulnerable", 1, 0]}},
            "victimas": {"$sum": {"$cond": ["$victima_conflicto", 1, 0]}},
            "discapacidad": {"$sum": {"$cond": ["$discapacidad_flag", 1, 0]}},
            "rurales": {"$sum": {"$cond": [{"$in": ["$tipo_ubicacion", ["Rural", "Semirural"]]}, 1, 0]}},
        }}
    ]).to_list(1)

    by_program = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$programa", "n": {"$sum": 1}, "prom": {"$avg": "$promedio"}}},
        {"$sort": {"n": -1}},
        {"$limit": 15},
        {"$project": {"_id": 0, "programa": "$_id", "n": 1, "prom": {"$round": ["$prom", 2]}}}
    ]).to_list(20)

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

    total_programas = len(await coll.distinct("programa", match))
    total_facultades = len(await coll.distinct("facultad", match))

    k = agg_kpi[0] if agg_kpi else {}
    return {
        "kpis": {
            "total": k.get("total", 0),
            "matriculados": k.get("matriculados", 0),
            "programas": total_programas,
            "facultades": total_facultades,
            "promedio": round(k.get("promedio", 0) or 0, 2),
            "avance_pct": round(k.get("avance_pct", 0) or 0, 1),
            "vulnerables": k.get("vulnerables", 0),
            "victimas": k.get("victimas", 0),
            "discapacidad": k.get("discapacidad", 0),
            "rurales": k.get("rurales", 0),
        },
        "by_program": by_program,
        "by_genero": by_genero,
        "by_estrato": by_estrato,
        "by_ubicacion": by_ubicacion,
    }


@router.get("/academic")
async def academic(match: dict = Depends(_common_params), user=Depends(get_current_user)):
    coll = db.students
    pipeline = [{"$match": match}] if match else []

    by_program_avg = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$programa", "prom": {"$avg": "$promedio"}, "n": {"$sum": 1},
                    "reprobadas": {"$avg": "$reprobadas"}, "aprobadas": {"$avg": "$aprobadas"}}},
        {"$sort": {"n": -1}},
        {"$limit": 20},
        {"$project": {"_id": 0, "programa": "$_id", "n": 1,
                      "prom": {"$round": ["$prom", 2]},
                      "reprobadas": {"$round": ["$reprobadas", 1]},
                      "aprobadas": {"$round": ["$aprobadas", 1]}}}
    ]).to_list(50)

    by_facultad = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$facultad", "prom": {"$avg": "$promedio"}, "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "facultad": "$_id", "prom": {"$round": ["$prom", 2]}, "n": 1}}
    ]).to_list(50)

    distribucion = await coll.aggregate(pipeline + [
        {"$bucket": {
            "groupBy": "$promedio",
            "boundaries": [0, 1, 2, 3, 3.5, 4, 4.5, 5.01],
            "default": "Otros",
            "output": {"n": {"$sum": 1}}
        }}
    ]).to_list(50)

    en_riesgo = await coll.count_documents({**match, "promedio": {"$lt": 3.0, "$gt": 0}})
    excelencia = await coll.count_documents({**match, "promedio": {"$gte": 4.5}})

    # Avance curricular por programa
    avance = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$programa", "avance": {"$avg": "$avance_pct"}, "n": {"$sum": 1}}},
        {"$sort": {"avance": -1}},
        {"$limit": 15},
        {"$project": {"_id": 0, "programa": "$_id", "avance": {"$round": ["$avance", 1]}, "n": 1}}
    ]).to_list(20)

    return {
        "by_program_avg": by_program_avg,
        "by_facultad": by_facultad,
        "distribucion_notas": distribucion,
        "en_riesgo": en_riesgo,
        "excelencia": excelencia,
        "avance": avance,
    }


@router.get("/territorial")
async def territorial(match: dict = Depends(_common_params), user=Depends(get_current_user)):
    coll = db.students
    pipeline = [{"$match": match}] if match else []

    municipios = await coll.aggregate(pipeline + [
        {"$group": {
            "_id": {"codigo": "$ciudad_codigo", "nombre": "$ciudad_nombre",
                    "lat": "$lat", "lon": "$lon", "departamento": "$departamento"},
            "n": {"$sum": 1},
            "prom": {"$avg": "$promedio"},
            "vulnerables": {"$sum": {"$cond": ["$grupo_vulnerable", 1, 0]}},
            "rural": {"$sum": {"$cond": [{"$in": ["$tipo_ubicacion", ["Rural", "Semirural"]]}, 1, 0]}},
        }},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "codigo": "$_id.codigo", "nombre": "$_id.nombre",
                      "lat": "$_id.lat", "lon": "$_id.lon",
                      "departamento": "$_id.departamento",
                      "n": 1, "prom": {"$round": ["$prom", 2]},
                      "vulnerables": 1, "rural": 1}}
    ]).to_list(2000)

    por_departamento = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$departamento", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "departamento": "$_id", "n": 1}}
    ]).to_list(50)

    return {"municipios": municipios, "por_departamento": por_departamento}


@router.get("/historical")
async def historical(programa: Optional[str] = None, user=Depends(get_current_user)):
    match = {}
    if programa:
        match["programa"] = programa
    items = await db.historico.find(match, {"_id": 0}).sort([("programa", 1), ("periodo", 1)]).to_list(2000)
    # Group by periodo for charts
    by_periodo = {}
    for it in items:
        by_periodo.setdefault(it["periodo"], []).append(it)
    series_periodo = []
    for per, items_p in sorted(by_periodo.items()):
        avg_prom = sum(i["promedio"] for i in items_p) / max(1, len(items_p))
        avg_apr = sum(i["tasa_aprobacion"] for i in items_p) / max(1, len(items_p))
        series_periodo.append({
            "periodo": per,
            "promedio": round(avg_prom, 2),
            "tasa_aprobacion": round(avg_apr, 1),
            "matriculados": sum(i["matriculados"] for i in items_p),
        })
    return {"by_program": items, "series_periodo": series_periodo}


@router.get("/filters")
async def filter_options(user=Depends(get_current_user)):
    """Return available filter values from the data. Includes facultad→programa map for cascading filters."""
    def _clean(values, invalid=None):
        invalid = invalid or {"SELECCIONE...", "SELECCIONE", "NO REGISTRA", ""}
        return sorted([v for v in values if v and str(v).strip().upper() not in invalid])

    programas = _clean(await db.students.distinct("programa"))
    facultades = _clean(await db.students.distinct("facultad"))
    periodos = sorted([p for p in await db.students.distinct("periodo") if p])
    generos = _clean(await db.students.distinct("genero"))
    estratos = _clean(await db.students.distinct("estrato"))
    etnias = _clean(await db.students.distinct("etnia"))
    ubicaciones = _clean(await db.students.distinct("tipo_ubicacion"))
    estados_matricula = _clean(await db.students.distinct("estado_matricula"))

    # facultad -> [programas] mapping for cascading filters
    pipe = [
        {"$match": {"facultad": {"$ne": None}, "programa": {"$ne": None}}},
        {"$group": {"_id": {"f": "$facultad", "p": "$programa"}}},
    ]
    facultad_programa = {}
    async for r in db.students.aggregate(pipe):
        f = r["_id"].get("f"); p = r["_id"].get("p")
        if not f or not p:
            continue
        facultad_programa.setdefault(f, set()).add(p)
    facultad_programa = {k: sorted(v) for k, v in facultad_programa.items()}

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
    }
