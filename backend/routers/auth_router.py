"""Auth router."""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from models import LoginIn, ChangePasswordIn, UserOut
from auth import verify_password, hash_password, create_token, get_current_user
from database import db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(data: LoginIn):
    """Login por CÉDULA (documento) o CORREO. Prioridad: cédula si la cadena es solo dígitos."""
    identifier = data.email.strip()
    is_numeric = identifier.isdigit()
    user = None
    if is_numeric:
        # Buscar por cédula/documento (cualquiera de los campos donde se almacena)
        user = await db.users.find_one({"$or": [
            {"documento": identifier},
            {"cedula": identifier},
        ]})
    if not user:
        # Fallback a correo (para superadmin y usuarios institucionales)
        user = await db.users.find_one({"email": identifier.lower()})
    if not user or not user.get("active", True):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = create_token({"sub": user["id"], "role": user["role"], "email": user["email"]})
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": datetime.utcnow().isoformat()}})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "documento": user.get("documento") or user.get("cedula"),
            "full_name": user["full_name"],
            "role": user["role"],
            "must_change_password": user.get("must_change_password", False),
            "download_enabled": user.get("download_enabled", user["role"] in ("superadmin", "admin")),
            "facultad_id": user.get("facultad_id"),
            "programa_id": user.get("programa_id"),
        },
    }


@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return user


@router.post("/change-password")
async def change_password(data: ChangePasswordIn, user=Depends(get_current_user)):
    full = await db.users.find_one({"id": user["id"]})
    if not verify_password(data.current_password, full["password"]):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener mínimo 6 caracteres")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password": hash_password(data.new_password), "must_change_password": False}},
    )
    return {"ok": True, "message": "Contraseña actualizada"}
