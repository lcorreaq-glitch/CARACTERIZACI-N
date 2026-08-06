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


async def _apply_docente_materia(match: dict, docente_id, materia_id, codigo_grupo=None) -> dict:
    """If docente_id/materia_id/codigo_grupo are present, restrict match to intersection
    of cédulas from historico_notas (docente/materia) and matriculas (grupo)."""
    cedulas_sets = []
    if codigo_grupo and codigo_grupo not in ("all", "todos", ""):
        cedulas = await db.matriculas.distinct("cedula", {"codigo_grupo": codigo_grupo})
        cedulas_sets.append(set(cedulas))
    hn_match = {}
    if docente_id and docente_id not in ("all", "todos", ""):
        hn_match["docente_id"] = docente_id
    if materia_id and materia_id not in ("all", "todos", ""):
        hn_match["materia_id"] = materia_id
    if hn_match:
        cedulas = await db.historico_notas.distinct("cedula", hn_match)
        cedulas_sets.append(set(cedulas))
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
):
    match = _build_match(locals())
    return await _apply_docente_materia(match, docente_id, materia_id, codigo_grupo)


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

    # Notas per periodo from historico_notas (source of truth)
    # Restringir por cédulas del match (si hay filtros que reducen students)
    if match:
        cedulas_match = await db.students.distinct("cedula", match)
        hn_match = {"cedula": {"$in": cedulas_match}}
    else:
        hn_match = {}
    notas_per_periodo = {}
    async for r in db.historico_notas.aggregate([
        {"$match": hn_match} if hn_match else {"$match": {}},
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
        {"$group": {"_id": "$rango_edad", "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "rango": "$_id", "n": 1}}
    ]).to_list(10)

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
        {"$match": {"departamento_residencia": {"$ne": None}}},
        {"$group": {"_id": "$departamento_residencia", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$limit": 15},
        {"$project": {"_id": 0, "departamento": "$_id", "n": 1}}
    ]).to_list(15)

    total_programas = len(await coll.distinct("programa", match))
    total_facultades = len(await coll.distinct("facultad", match))

    # Promedio general PONDERADO desde historico_notas (nota real, no promedio de promedios)
    prom_ponderado = 0
    if not match or match.get("cedula", {}).get("$in") is not None or not match:
        hn_match_general = hn_match if match else {}
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
        "by_vulnerabilidad": by_vulnerabilidad,
        "by_pais": by_pais,
        "by_departamento": by_departamento,
    }


@router.get("/academic")
async def academic(match: dict = Depends(_common_params), user=Depends(get_current_user)):
    coll = db.students
    pipeline = [{"$match": match}] if match else []

    by_program_avg = await coll.aggregate(pipeline + [
        {"$group": {
            "_id": "$programa", "n": {"$sum": 1},
            "prom": {"$avg": {"$cond": [{"$gt": ["$promedio", 0]}, "$promedio", None]}},
            "prom_2025_2": {"$avg": {"$cond": [{"$gt": ["$promedio_2025_2", 0]}, "$promedio_2025_2", None]}},
            "prom_2026_1": {"$avg": {"$cond": [{"$gt": ["$promedio_2026_1", 0]}, "$promedio_2026_1", None]}},
            "con_notas": {"$sum": {"$cond": [{"$gt": ["$promedio", 0]}, 1, 0]}},
        }},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "programa": "$_id", "n": 1,
                      "con_notas": 1,
                      "prom": {"$round": [{"$ifNull": ["$prom", 0]}, 2]},
                      "prom_2025_2": {"$round": [{"$ifNull": ["$prom_2025_2", 0]}, 2]},
                      "prom_2026_1": {"$round": [{"$ifNull": ["$prom_2026_1", 0]}, 2]}}}
    ]).to_list(100)

    by_facultad = await coll.aggregate(pipeline + [
        {"$group": {
            "_id": "$facultad", "n": {"$sum": 1},
            "prom": {"$avg": {"$cond": [{"$gt": ["$promedio", 0]}, "$promedio", None]}},
            "prom_2025_2": {"$avg": {"$cond": [{"$gt": ["$promedio_2025_2", 0]}, "$promedio_2025_2", None]}},
            "prom_2026_1": {"$avg": {"$cond": [{"$gt": ["$promedio_2026_1", 0]}, "$promedio_2026_1", None]}},
            "con_notas": {"$sum": {"$cond": [{"$gt": ["$promedio", 0]}, 1, 0]}},
        }},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "facultad": "$_id", "n": 1, "con_notas": 1,
                      "prom": {"$round": [{"$ifNull": ["$prom", 0]}, 2]},
                      "prom_2025_2": {"$round": [{"$ifNull": ["$prom_2025_2", 0]}, 2]},
                      "prom_2026_1": {"$round": [{"$ifNull": ["$prom_2026_1", 0]}, 2]}}}
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

    # Docentes y materias para filtros globales
    docentes_rows = await db.users.find({"role": "docente"}, {"_id": 0, "id": 1, "full_name": 1, "email": 1}).to_list(1000)
    docentes = sorted([{"id": d["id"], "nombre": d.get("full_name") or d.get("email", "")} for d in docentes_rows], key=lambda x: x["nombre"])

    materias_rows = await db.materias.find({}, {"_id": 0, "id": 1, "nombre": 1, "codigo": 1}).to_list(5000)
    materias = sorted(
        [{"id": m["id"], "nombre": m.get("nombre", ""), "codigo": m.get("codigo", "")} for m in materias_rows],
        key=lambda x: x["nombre"],
    )

    # Grupos activos (limitados a los 200 más relevantes o filtrados por rol)
    grupos_query = {}
    if user.get("role") == "docente":
        grupos_query = {"docente_id": user["id"]}
    grupos_rows = await db.grupos.find(grupos_query, {
        "_id": 0, "codigo_grupo": 1, "asignatura_nombre": 1,
        "programa": 1, "docente_nombre": 1, "periodo": 1
    }).sort("codigo_grupo", 1).to_list(2000)
    grupos = [
        {"id": g["codigo_grupo"],
         "nombre": f"{g.get('asignatura_nombre', '')[:35]}",
         "codigo": g["codigo_grupo"],
         "programa": g.get("programa", "")[:30],
         "docente": g.get("docente_nombre", "")}
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
