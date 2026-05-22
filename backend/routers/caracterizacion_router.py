"""Caracterización sociodemográfica completa, filtrable por facultad/programa/periodo."""
from typing import Optional
from fastapi import APIRouter, Depends
from auth import get_current_user
from database import db

router = APIRouter(prefix="/api/caracterizacion", tags=["caracterizacion"])


def _build_match(args: dict) -> dict:
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
        "departamento": "departamento",
        "rango_edad": "rango_edad",
        "rango_ingresos": "rango_ingresos",
    }
    for k, field in mapping.items():
        v = args.get(k)
        if v not in (None, "", "all", "todos"):
            m[field] = v
    for k, field in {"sisben": "sisben_tiene", "discapacidad": "discapacidad_flag",
                     "victima": "victima_conflicto", "grupo_vulnerable": "grupo_vulnerable",
                     "vivienda_propia": "vivienda_propia", "resguardo_indigena": "resguardo_indigena"}.items():
        v = args.get(k)
        if v in ("true", "1", True):
            m[field] = True
        elif v in ("false", "0", False):
            m[field] = False
    return m


def _params(
    periodo: Optional[str] = None,
    facultad: Optional[str] = None,
    programa: Optional[str] = None,
    genero: Optional[str] = None,
    estrato: Optional[str] = None,
    etnia: Optional[str] = None,
    tipo_ubicacion: Optional[str] = None,
    estado_matricula: Optional[str] = None,
    municipio_codigo: Optional[str] = None,
    departamento: Optional[str] = None,
    rango_edad: Optional[str] = None,
    rango_ingresos: Optional[str] = None,
    sisben: Optional[str] = None,
    discapacidad: Optional[str] = None,
    victima: Optional[str] = None,
    grupo_vulnerable: Optional[str] = None,
    vivienda_propia: Optional[str] = None,
    resguardo_indigena: Optional[str] = None,
):
    return _build_match(locals())


async def _group(match, field, limit=20, sort_alpha=False):
    pipe = [{"$match": match}] if match else []
    pipe += [
        {"$group": {"_id": f"${field}", "n": {"$sum": 1}}},
    ]
    if sort_alpha:
        pipe.append({"$sort": {"_id": 1}})
    else:
        pipe.append({"$sort": {"n": -1}})
    pipe += [{"$limit": limit}, {"$project": {"_id": 0, "label": "$_id", "n": 1}}]
    res = await db.students.aggregate(pipe).to_list(limit)
    # Convert booleans to legible
    for r in res:
        if r.get("label") is True:
            r["label"] = "Sí"
        elif r.get("label") is False:
            r["label"] = "No"
        elif r.get("label") is None or r.get("label") == "":
            r["label"] = "Sin dato"
        else:
            r["label"] = str(r["label"])
    return res


async def _group_array(match, field, limit=15):
    """For array fields like hobbies_cat / actividades_cat — unwind first."""
    pipe = [{"$match": match}] if match else []
    pipe += [
        {"$unwind": {"path": f"${field}", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": f"${field}", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "label": "$_id", "n": 1}},
    ]
    return await db.students.aggregate(pipe).to_list(limit)


@router.get("/overview")
async def overview(match: dict = Depends(_params), user=Depends(get_current_user)):
    total = await db.students.count_documents(match)
    if total == 0:
        return {"total": 0, "blocks": {}}

    # Blocks of analysis
    blocks = {
        "personal": {
            "genero": await _group(match, "genero", 10),
            "rango_edad": await _group(match, "rango_edad", 10, sort_alpha=True),
            "estado_civil": await _group(match, "estado_civil", 10),
            "tipo_documento": await _group(match, "tipo_documento", 10),
        },
        "socioeconomico": {
            "estrato": await _group(match, "estrato", 10, sort_alpha=True),
            "rango_ingresos": await _group(match, "rango_ingresos", 10),
            "sisben_nivel": await _group(match, "sisben_nivel", 30, sort_alpha=True),
            "grupo_sisben": await _group(match, "grupo_sisben", 10, sort_alpha=True),
            "vivienda_propia": await _group(match, "vivienda_propia", 5),
            "deuda_vivienda": await _group(match, "deuda_vivienda", 5),
            "num_personas_flia": await _group(match, "num_personas_flia", 10, sort_alpha=True),
            "num_aportantes": await _group(match, "num_aportantes", 10, sort_alpha=True),
        },
        "territorial": {
            "tipo_ubicacion": await _group(match, "tipo_ubicacion", 10),
            "departamento": await _group(match, "departamento", 25),
            "zona_frontera": await _group(match, "zona_frontera", 10),
        },
        "etnico_diferencial": {
            "etnia": await _group(match, "etnia", 10),
            "grupo_etnia": await _group(match, "grupo_etnia", 10),
            "resguardo_indigena": await _group(match, "resguardo_indigena", 5),
            "discapacidad_flag": await _group(match, "discapacidad_flag", 5),
            "discapacidad_tipo": await _group(match, "discapacidad_tipo", 10),
            "capacidad_excepcional": await _group(match, "capacidad_excepcional", 10),
        },
        "vulnerabilidad": {
            "grupo_vulnerable": await _group(match, "grupo_vulnerable", 5),
            "tipo_grupo_vulnerable": await _group(match, "tipo_grupo_vulnerable", 10),
            "victima_conflicto": await _group(match, "victima_conflicto", 5),
            "veterano": await _group(match, "veterano", 5),
        },
        "familiar": {
            "nivel_educ_madre": await _group(match, "nivel_educ_madre", 10),
            "nivel_educ_padre": await _group(match, "nivel_educ_padre", 10),
            "hnos_educ_superior": await _group(match, "hnos_educ_superior", 10, sort_alpha=True),
            "parentesco_emergencia": await _group(match, "parentesco_emergencia", 10),
        },
        "vocacional": {
            "razon_carrera": await _group(match, "razon_carrera_cat", 10),
            "razon_institucion": await _group(match, "razon_institucion", 10),
            "hobbies": await _group_array(match, "hobbies_cat", 10),
            "actividades": await _group_array(match, "actividades_cat", 10),
            "tiene_distinciones": await _group(match, "tiene_distinciones", 5),
        },
    }

    # Key KPIs
    kpi_pipe = [{"$match": match}] + [{"$group": {
        "_id": None,
        "promedio_edad": {"$avg": "$edad"},
        "promedio_ingresos": {"$avg": "$ingresos_flia"},
        "promedio_academico": {"$avg": "$promedio"},
        "victimas": {"$sum": {"$cond": ["$victima_conflicto", 1, 0]}},
        "vulnerables": {"$sum": {"$cond": ["$grupo_vulnerable", 1, 0]}},
        "discapacidad": {"$sum": {"$cond": ["$discapacidad_flag", 1, 0]}},
        "sisben": {"$sum": {"$cond": ["$sisben_tiene", 1, 0]}},
        "rural": {"$sum": {"$cond": [{"$in": ["$tipo_ubicacion", ["Rural", "Semirural"]]}, 1, 0]}},
    }}]
    kagg = await db.students.aggregate(kpi_pipe).to_list(1)
    k = kagg[0] if kagg else {}

    return {
        "total": total,
        "kpis": {
            "promedio_edad": round(k.get("promedio_edad", 0) or 0, 1),
            "promedio_ingresos": round(k.get("promedio_ingresos", 0) or 0, 0),
            "promedio_academico": round(k.get("promedio_academico", 0) or 0, 2),
            "victimas_pct": round(k.get("victimas", 0) / total * 100, 1),
            "vulnerables_pct": round(k.get("vulnerables", 0) / total * 100, 1),
            "discapacidad_pct": round(k.get("discapacidad", 0) / total * 100, 1),
            "sisben_pct": round(k.get("sisben", 0) / total * 100, 1),
            "rural_pct": round(k.get("rural", 0) / total * 100, 1),
        },
        "blocks": blocks,
    }
