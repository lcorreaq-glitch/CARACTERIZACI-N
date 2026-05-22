"""DIVIPOLA admin: CRUD municipalities/cities (national + international).
Persists to MongoDB collection 'divipola_municipios' (overrides static list).
"""
from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_user, require_roles
from database import db
from divipola import MUNICIPIOS as STATIC_MUNICIPIOS

router = APIRouter(prefix="/api/admin/divipola", tags=["divipola"])


class MunicipioIn(BaseModel):
    codigo: str
    nombre: str
    departamento: str
    pais: str = "COLOMBIA"
    lat: float
    lon: float


@router.get("")
async def list_municipios(user=Depends(get_current_user)):
    items = await db.divipola_municipios.find({}, {"_id": 0}).sort([("pais", 1), ("departamento", 1), ("nombre", 1)]).to_list(5000)
    if not items:
        # Seed from static
        await _seed_static()
        items = await db.divipola_municipios.find({}, {"_id": 0}).sort([("pais", 1), ("departamento", 1), ("nombre", 1)]).to_list(5000)
    return items


async def _seed_static():
    docs = []
    for m in STATIC_MUNICIPIOS:
        is_intl = m["departamento"] in (
            "VENEZUELA", "ECUADOR", "PANAMA", "ESTADOS UNIDOS",
            "ESPAÑA", "CHILE", "ARGENTINA", "MEXICO", "PERU"
        )
        docs.append({
            "id": str(uuid.uuid4()),
            "codigo": m["codigo"],
            "nombre": m["nombre"],
            "departamento": m["departamento"],
            "pais": m["departamento"] if is_intl else "COLOMBIA",
            "lat": m["lat"],
            "lon": m["lon"],
            "fuente": "DANE/Institucional",
            "created_at": datetime.utcnow().isoformat(),
        })
    if docs:
        await db.divipola_municipios.insert_many(docs)


@router.post("")
async def create_municipio(payload: MunicipioIn, user=Depends(require_roles("superadmin", "admin"))):
    if await db.divipola_municipios.find_one({"codigo": payload.codigo}):
        raise HTTPException(400, "Código ya existe")
    doc = payload.model_dump()
    doc.update({
        "id": str(uuid.uuid4()),
        "fuente": "Manual",
        "created_at": datetime.utcnow().isoformat(),
    })
    await db.divipola_municipios.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.patch("/{municipio_id}")
async def update_municipio(municipio_id: str, payload: MunicipioIn, user=Depends(require_roles("superadmin", "admin"))):
    upd = payload.model_dump()
    await db.divipola_municipios.update_one({"id": municipio_id}, {"$set": upd})
    return await db.divipola_municipios.find_one({"id": municipio_id}, {"_id": 0})


@router.delete("/{municipio_id}")
async def delete_municipio(municipio_id: str, user=Depends(require_roles("superadmin"))):
    await db.divipola_municipios.delete_one({"id": municipio_id})
    return {"ok": True}


@router.get("/paises")
async def list_paises(user=Depends(get_current_user)):
    """Listado distintivo de países con conteo de municipios."""
    pipe = [
        {"$group": {"_id": "$pais", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
        {"$project": {"_id": 0, "pais": "$_id", "n": 1}},
    ]
    return await db.divipola_municipios.aggregate(pipe).to_list(200)
