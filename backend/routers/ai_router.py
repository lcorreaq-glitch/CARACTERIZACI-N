"""AI Insights via Emergent LLM Key (GPT-5.4)."""
import os
import json
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from database import db
from scope import apply_role_scope
from models import AIInsightIn
from emergentintegrations.llm.chat import LlmChat, UserMessage

router = APIRouter(prefix="/api/ai", tags=["ai"])

EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

SYSTEM_PROMPT = """Eres un analista experto en datos académicos institucionales para la IU Digital de Antioquia.
Recibes métricas resumidas de un dashboard y debes producir insights ejecutivos en ESPAÑOL.

REGLAS DE SALIDA:
1. Comienza con un párrafo ejecutivo de 2-3 frases.
2. Luego 4-6 hallazgos clave en bullets cortos. Cada bullet con un emoji o icono textual breve.
3. Termina con 2-3 recomendaciones accionables específicas para permanencia/acreditación/equidad.
4. Sé directo, evita formalismos vacíos. Usa números reales del contexto.
5. Si los datos están vacíos, indícalo y sugiere primero cargar archivos."""


async def _gather_context(scope: str, filters: dict = None):
    """Quick aggregation snapshot for the model."""
    match = filters or {}
    coll = db.students
    total = await coll.count_documents(match)
    if total == 0:
        return {"empty": True}
    pipeline = [{"$match": match}] if match else []
    base = await coll.aggregate(pipeline + [{"$group": {
        "_id": None,
        "total": {"$sum": 1},
        "promedio": {"$avg": "$promedio"},
        "vulnerables": {"$sum": {"$cond": ["$grupo_vulnerable", 1, 0]}},
        "victimas": {"$sum": {"$cond": ["$victima_conflicto", 1, 0]}},
        "rurales": {"$sum": {"$cond": [{"$in": ["$tipo_ubicacion", ["Rural", "Semirural"]]}, 1, 0]}},
        "en_riesgo": {"$sum": {"$cond": [{"$and": [{"$gt": ["$promedio", 0]}, {"$lt": ["$promedio", 3.0]}]}, 1, 0]}},
    }}]).to_list(1)
    progs = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$programa", "n": {"$sum": 1}, "prom": {"$avg": "$promedio"}}},
        {"$sort": {"n": -1}}, {"$limit": 10},
        {"$project": {"_id": 0, "programa": "$_id", "n": 1, "prom": {"$round": ["$prom", 2]}}}
    ]).to_list(20)
    estratos = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$estrato", "n": {"$sum": 1}}}, {"$sort": {"_id": 1}}
    ]).to_list(20)
    municipios = await coll.aggregate(pipeline + [
        {"$group": {"_id": "$ciudad_nombre", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}, {"$limit": 10}
    ]).to_list(20)
    return {
        "scope": scope,
        "totales": base[0] if base else {},
        "top_programas": progs,
        "estratos": estratos,
        "top_municipios": municipios,
    }


@router.post("/insights")
async def generate_insights(payload: AIInsightIn, user=Depends(get_current_user)):
    filters = payload.filters.model_dump(exclude_none=True) if payload.filters else {}
    # Translate booleans
    mongo_match = {}
    for k, v in filters.items():
        if k == "sisben":
            mongo_match["sisben_tiene"] = v
        elif k == "discapacidad":
            mongo_match["discapacidad_flag"] = v
        elif k == "victima":
            mongo_match["victima_conflicto"] = v
        elif k == "grupo_vulnerable":
            mongo_match["grupo_vulnerable"] = v
        elif k == "municipio_codigo":
            mongo_match["ciudad_codigo"] = v
        elif v not in (None, "", "all"):
            mongo_match[k] = v

    ctx = await _gather_context(payload.scope, mongo_match)
    if ctx.get("empty"):
        return {
            "scope": payload.scope,
            "insight": "No se encontraron datos con los filtros aplicados. Cargue archivos de caracterización o relaje los filtros.",
            "model": "gpt-4o",
        }

    user_text = f"""Contexto JSON del dashboard '{payload.scope}':
{json.dumps(ctx, ensure_ascii=False, indent=2)}

{'Pregunta específica del usuario: ' + payload.question if payload.question else 'Genera el resumen ejecutivo.'}"""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"insights-{user['id']}",
            system_message=SYSTEM_PROMPT,
        ).with_model("openai", "gpt-4o")
        msg = UserMessage(text=user_text)
        resp = await chat.send_message(msg)
    except Exception as e:
        raise HTTPException(500, f"Error generando insight: {e}")

    return {"scope": payload.scope, "insight": resp, "model": "gpt-4o", "context_summary": ctx}



# =============================================================================
# ALERTAS TEMPRANAS IA — para Docentes (por estudiante y por grupo)
# =============================================================================

SYSTEM_PROMPT_ALERTA_ESTUDIANTE = """Eres un mentor pedagógico experto en permanencia estudiantil de la IU Digital de Antioquia.
Recibes datos reales de UN estudiante en riesgo: sus notas, promedio, y factores de vulnerabilidad
(SISBEN, víctima del conflicto, discapacidad, ruralidad, estrato bajo, etc.).

Tu tarea: producir una **alerta temprana accionable en español**, escrita EN 2ª PERSONA hacia el docente que la va a leer.
Estructura obligatoria (usa exactamente estos títulos con markdown):

**Diagnóstico**
1-2 oraciones claras que integren rendimiento + vulnerabilidad. Nombra al estudiante en 1ª referencia y luego usa "el/la estudiante".

**Factores de riesgo detectados**
Bullets cortos (máx 5), cada uno con un icono textual: 📉 (notas bajas), 🏠 (vulnerabilidad social),
♿ (discapacidad), 🌾 (rural), 💰 (SISBEN/estrato), 🔴 (víctima).

**Plan de intervención sugerido**
Numera 3-4 acciones CONCRETAS y REALIZABLES por un docente virtual: contacto proactivo con canal específico
(email/WhatsApp), tutoría particular, referir a bienestar universitario, seguimiento semanal, etc.
Cada acción con verbo imperativo al inicio (Contactar, Programar, Referir, Habilitar, Documentar).

**Nota importante**
Una oración de cierre empática recordando que la alerta es predictiva y busca prevenir la deserción.

REGLAS: máximo 250 palabras totales. No inventes datos. Si un dato no está en el contexto, no lo menciones.
Sé cálido pero profesional. Nada de emojis extra al inicio/final."""

SYSTEM_PROMPT_RESUMEN_GRUPO = """Eres un analista pedagógico institucional de la IU Digital de Antioquia.
Recibes las métricas agregadas de UN grupo/curso: total de estudiantes, promedio, estudiantes en riesgo,
distribución de vulnerabilidad, y una lista breve de los casos más críticos.

Produce un **resumen ejecutivo en español** para el docente titular. Estructura obligatoria:

**Estado general del grupo**
2 frases: cifra global de riesgo, promedio, tendencia si existe.

**Focos prioritarios**
3-5 bullets con los patrones más relevantes (ej: "40% con SISBEN A/B", "3 estudiantes con score > 40").
Cada bullet con icono textual (📉📊🚨🌾♿💰🔴).

**Recomendaciones de intervención colectiva**
2-3 acciones a nivel de grupo (no individuales): tutorías grupales, refuerzo temático, contacto con bienestar,
comunicación institucional, etc.

Máximo 200 palabras. Sé directo y accionable."""


async def _check_ai_enabled_for_docente(user):
    """AI toggle applies to profesor/decano/coordinador. Superadmin/direccion bypass."""
    if user.get("role") in ("superadmin", "direccion"):
        return
    settings = await db.system_settings.find_one({"_id": "global"}, {"_id": 0}) or {}
    if not settings.get("docente_ai_insights_enabled", True):
        raise HTTPException(
            status_code=403,
            detail="El módulo de IA está deshabilitado por el administrador.",
        )


async def _is_my_student(user, cedula: str) -> bool:
    """superadmin/direccion bypass. profesor: check grupos. decano/coordinador: check scope."""
    role = user.get("role")
    if role in ("superadmin", "direccion"):
        return True
    if role == "profesor":
        grupos = await db.grupos.find({"docente_id": user["id"]}, {"_id": 0, "codigo_grupo": 1}).to_list(1000)
        codigos = [g["codigo_grupo"] for g in grupos]
        if not codigos:
            return False
        hit = await db.matriculas.find_one({"codigo_grupo": {"$in": codigos}, "cedula": cedula})
        return hit is not None
    if role in ("decano", "coordinador"):
        scope_match = apply_role_scope(user, {"cedula": cedula})
        if "_no_scope_" in scope_match:
            return False
        cnt = await db.students.count_documents(scope_match)
        return cnt > 0
    return False


@router.post("/docente/alerta-estudiante")
async def alerta_estudiante(payload: dict, user=Depends(get_current_user)):
    """Genera una alerta temprana personalizada con IA para un estudiante en riesgo.
    Body: {cedula: str, codigo_grupo?: str}
    """
    await _check_ai_enabled_for_docente(user)

    cedula = (payload or {}).get("cedula")
    codigo_grupo = (payload or {}).get("codigo_grupo")
    if not cedula:
        raise HTTPException(400, "Falta la cédula del estudiante")

    if not await _is_my_student(user, cedula):
        raise HTTPException(403, "No tiene acceso a este estudiante")

    est = await db.students.find_one(
        {"cedula": cedula},
        {"_id": 0, "cedula": 1, "nombre": 1, "apellidos": 1, "nombre_completo": 1,
         "programa": 1, "facultad": 1, "nivel": 1, "correo_institucional": 1,
         "promedio": 1, "avance_pct": 1, "sisben_nivel": 1, "grupo_sisben": 1, "estrato": 1,
         "victima_conflicto": 1, "grupo_vulnerable": 1, "discapacidad_flag": 1,
         "tipo_ubicacion": 1, "ciudad_nombre": 1, "departamento": 1, "genero": 1, "edad": 1},
    )
    if not est:
        raise HTTPException(404, "Estudiante no encontrado")

    # Últimas notas (máx 12)
    notas_query = {"cedula": cedula}
    if codigo_grupo:
        notas_query["codigo_grupo"] = codigo_grupo
    elif user.get("role") == "profesor":
        notas_query["docente_id"] = user["id"]

    notas = await db.historico_notas.find(
        notas_query,
        {"_id": 0, "asignatura_nombre": 1, "nota": 1, "estado": 1, "periodo": 1, "aprobada": 1},
    ).sort([("periodo", -1)]).to_list(12)

    prom_notas = round(sum(n.get("nota", 0) for n in notas) / len(notas), 2) if notas else None

    ctx = {
        "estudiante": {
            "nombre": est.get("nombre_completo") or f"{est.get('nombre', '')} {est.get('apellidos', '')}".strip(),
            "programa": est.get("programa"),
            "facultad": est.get("facultad"),
            "nivel_actual": est.get("nivel"),
            "edad": est.get("edad"),
            "genero": est.get("genero"),
            "ubicacion": f"{est.get('ciudad_nombre', '')} · {est.get('departamento', '')}",
            "tipo_ubicacion": est.get("tipo_ubicacion"),
        },
        "academico": {
            "promedio_general": est.get("promedio"),
            "avance_pct": est.get("avance_pct"),
            "promedio_notas_recientes": prom_notas,
            "notas_recientes": notas[:8],
        },
        "vulnerabilidad": {
            "estrato": est.get("estrato"),
            "sisben_nivel": est.get("sisben_nivel"),
            "grupo_sisben": est.get("grupo_sisben"),
            "victima_conflicto": est.get("victima_conflicto"),
            "grupo_vulnerable": est.get("grupo_vulnerable"),
            "discapacidad": est.get("discapacidad_flag"),
        },
    }

    user_text = f"""Datos reales del estudiante en riesgo:

{json.dumps(ctx, ensure_ascii=False, indent=2, default=str)}

Genera la alerta temprana siguiendo la estructura obligatoria."""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"alerta-{user['id']}-{cedula}",
            system_message=SYSTEM_PROMPT_ALERTA_ESTUDIANTE,
        ).with_model("openai", "gpt-4o")
        msg = UserMessage(text=user_text)
        resp = await chat.send_message(msg)
    except Exception as e:
        raise HTTPException(500, f"Error generando alerta IA: {e}")

    return {
        "cedula": cedula,
        "estudiante_nombre": ctx["estudiante"]["nombre"],
        "alerta": resp,
        "context": ctx,
        "model": "gpt-4o",
    }


@router.post("/docente/resumen-grupo")
async def resumen_grupo(payload: dict, user=Depends(get_current_user)):
    """Resumen ejecutivo IA para un grupo del docente.
    Body: {codigo_grupo: str}
    """
    await _check_ai_enabled_for_docente(user)

    codigo_grupo = (payload or {}).get("codigo_grupo")
    if not codigo_grupo:
        raise HTTPException(400, "Falta codigo_grupo")

    # Validar que sea del docente
    grupo = await db.grupos.find_one({"codigo_grupo": codigo_grupo}, {"_id": 0})
    if not grupo:
        raise HTTPException(404, "Grupo no encontrado")
    if user.get("role") == "profesor" and grupo.get("docente_id") != user["id"]:
        raise HTTPException(403, "No tiene acceso a este grupo")

    # Cédulas del grupo
    cedulas = await db.matriculas.distinct("cedula", {"codigo_grupo": codigo_grupo})
    # Enforce scope for decano/coordinador: only cedulas belonging to their scope
    if user.get("role") in ("decano", "coordinador"):
        scope_match = apply_role_scope(user, {"cedula": {"$in": cedulas}})
        if "_no_scope_" in scope_match or not cedulas:
            raise HTTPException(403, "Este grupo no pertenece a su facultad/programa asignado")
        cedulas = await db.students.distinct("cedula", scope_match)
        if not cedulas:
            raise HTTPException(403, "Este grupo no pertenece a su facultad/programa asignado")
    if not cedulas:
        return {
            "codigo_grupo": codigo_grupo,
            "asignatura_nombre": grupo.get("asignatura_nombre"),
            "resumen": "Este grupo no tiene estudiantes matriculados. No hay datos suficientes para generar un análisis.",
            "model": "gpt-4o",
        }

    match = {"cedula": {"$in": cedulas}}
    total = len(cedulas)

    agg = await db.students.aggregate([
        {"$match": match},
        {"$group": {
            "_id": None,
            "promedio": {"$avg": "$promedio"},
            "vulnerables": {"$sum": {"$cond": ["$grupo_vulnerable", 1, 0]}},
            "victimas": {"$sum": {"$cond": ["$victima_conflicto", 1, 0]}},
            "discapacidad": {"$sum": {"$cond": ["$discapacidad_flag", 1, 0]}},
            "rural": {"$sum": {"$cond": [{"$in": ["$tipo_ubicacion", ["Rural", "Semirural"]]}, 1, 0]}},
            "sisben_ab": {"$sum": {"$cond": [{"$regexMatch": {"input": {"$ifNull": ["$sisben_nivel", ""]}, "regex": "^[AB]"}}, 1, 0]}},
        }},
    ]).to_list(1)

    en_riesgo = await db.students.count_documents({**match, "promedio": {"$lt": 3.0, "$gt": 0}})
    excelencia = await db.students.count_documents({**match, "promedio": {"$gte": 4.5}})

    # Top 5 en riesgo con más score (usa la misma lógica del endpoint /en-riesgo, simplificado)
    top_riesgo = await db.students.find(
        {**match, "promedio": {"$lt": 3.0, "$gt": 0}},
        {"_id": 0, "nombre_completo": 1, "nombre": 1, "apellidos": 1,
         "promedio": 1, "sisben_nivel": 1, "victima_conflicto": 1, "grupo_vulnerable": 1},
    ).sort("promedio", 1).limit(5).to_list(5)

    k = agg[0] if agg else {}
    ctx = {
        "grupo": {
            "codigo": codigo_grupo,
            "asignatura": grupo.get("asignatura_nombre"),
            "programa": grupo.get("programa"),
            "periodo": grupo.get("periodo"),
            "docente": grupo.get("docente_nombre"),
        },
        "totales": {
            "estudiantes": total,
            "promedio": round(k.get("promedio", 0) or 0, 2),
            "en_riesgo": en_riesgo,
            "excelencia": excelencia,
            "vulnerables": k.get("vulnerables", 0),
            "victimas_conflicto": k.get("victimas", 0),
            "discapacidad": k.get("discapacidad", 0),
            "rurales": k.get("rural", 0),
            "sisben_ab": k.get("sisben_ab", 0),
        },
        "top_casos_criticos": [
            {
                "nombre": s.get("nombre_completo") or f"{s.get('nombre', '')} {s.get('apellidos', '')}".strip(),
                "promedio": s.get("promedio"),
                "sisben": s.get("sisben_nivel"),
                "victima": s.get("victima_conflicto", False),
                "vulnerable": s.get("grupo_vulnerable", False),
            }
            for s in top_riesgo
        ],
    }

    user_text = f"""Métricas reales del grupo:

{json.dumps(ctx, ensure_ascii=False, indent=2, default=str)}

Genera el resumen ejecutivo siguiendo la estructura obligatoria."""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"resumen-grupo-{user['id']}-{codigo_grupo}",
            system_message=SYSTEM_PROMPT_RESUMEN_GRUPO,
        ).with_model("openai", "gpt-4o")
        msg = UserMessage(text=user_text)
        resp = await chat.send_message(msg)
    except Exception as e:
        raise HTTPException(500, f"Error generando resumen IA: {e}")

    return {
        "codigo_grupo": codigo_grupo,
        "asignatura_nombre": grupo.get("asignatura_nombre"),
        "resumen": resp,
        "context": ctx,
        "model": "gpt-4o",
    }
