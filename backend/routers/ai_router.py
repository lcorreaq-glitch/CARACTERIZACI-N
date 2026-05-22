"""AI Insights via Emergent LLM Key (GPT-5.4)."""
import os
import json
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from database import db
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
            "model": "gpt-5.4",
        }

    user_text = f"""Contexto JSON del dashboard '{payload.scope}':
{json.dumps(ctx, ensure_ascii=False, indent=2)}

{'Pregunta específica del usuario: ' + payload.question if payload.question else 'Genera el resumen ejecutivo.'}"""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"insights-{user['id']}",
            system_message=SYSTEM_PROMPT,
        ).with_model("openai", "gpt-5.4")
        msg = UserMessage(text=user_text)
        resp = await chat.send_message(msg)
    except Exception as e:
        raise HTTPException(500, f"Error generando insight: {e}")

    return {"scope": payload.scope, "insight": resp, "model": "gpt-5.4", "context_summary": ctx}
