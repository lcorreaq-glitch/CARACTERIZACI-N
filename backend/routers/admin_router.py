"""Admin router: users, facultades, programas, materias, periodos, docente-materia."""
from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from models import UserCreate, UserUpdate, CatalogIn, DocenteMateriaIn
from auth import hash_password, get_current_user, require_roles
from database import db

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------- Users ----------
@router.get("/users")
async def list_users(user=Depends(require_roles("superadmin", "admin"))):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return users


@router.post("/users")
async def create_user(payload: UserCreate, user=Depends(require_roles("superadmin"))):
    if await db.users.find_one({"email": payload.email.lower()}):
        raise HTTPException(400, "Email ya existe")
    new = {
        "id": str(uuid.uuid4()),
        "email": payload.email.lower(),
        "password": hash_password(payload.password),
        "full_name": payload.full_name,
        "role": payload.role,
        "facultad_id": payload.facultad_id,
        "programa_id": payload.programa_id,
        "active": True,
        "must_change_password": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.users.insert_one(new)
    new.pop("password", None)
    new.pop("_id", None)
    return new


@router.patch("/users/{user_id}")
async def update_user(user_id: str, payload: UserUpdate, user=Depends(require_roles("superadmin"))):
    upd = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not upd:
        raise HTTPException(400, "Nada que actualizar")
    res = await db.users.update_one({"id": user_id}, {"$set": upd})
    if not res.matched_count:
        raise HTTPException(404, "Usuario no encontrado")
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return u


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user=Depends(require_roles("superadmin"))):
    if user_id == user["id"]:
        raise HTTPException(400, "No puedes eliminar tu propio usuario")
    await db.users.delete_one({"id": user_id})
    return {"ok": True}


# ---------- Catalog helpers ----------
def _catalog_router(name: str, collection: str):
    @router.get(f"/{name}")
    async def _list(user=Depends(get_current_user)):
        items = await db[collection].find({}, {"_id": 0}).sort("nombre", 1).to_list(5000)
        return items

    @router.post(f"/{name}")
    async def _create(payload: CatalogIn, user=Depends(require_roles("superadmin", "admin"))):
        doc = {
            "id": str(uuid.uuid4()),
            "nombre": payload.nombre,
            "codigo": payload.codigo,
            "facultad_id": payload.facultad_id,
            "programa_id": payload.programa_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        await db[collection].insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.delete(f"/{name}/{{item_id}}")
    async def _delete(item_id: str, user=Depends(require_roles("superadmin", "admin"))):
        await db[collection].delete_one({"id": item_id})
        return {"ok": True}

    return _list, _create, _delete


# Register catalog endpoints
_catalog_router("facultades", "facultades")
_catalog_router("programas", "programas")
_catalog_router("materias", "materias")
_catalog_router("periodos", "periodos")


# ---------- Docente-Materia ----------
@router.get("/docente-materia")
async def list_docente_materia(user=Depends(get_current_user)):
    items = await db.docente_materia.find({}, {"_id": 0}).to_list(5000)
    return items


@router.post("/docente-materia")
async def create_docente_materia(payload: DocenteMateriaIn, user=Depends(require_roles("superadmin", "admin"))):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.utcnow().isoformat()
    await db.docente_materia.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.delete("/docente-materia/{item_id}")
async def delete_dm(item_id: str, user=Depends(require_roles("superadmin", "admin"))):
    await db.docente_materia.delete_one({"id": item_id})
    return {"ok": True}
