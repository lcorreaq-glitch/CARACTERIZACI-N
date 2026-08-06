"""JWT + bcrypt auth utilities."""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "720"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(payload: dict) -> str:
    data = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    from database import db
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if user.get("active") is False:
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    # Enrich with scope names (facultad_nombre, programa_nombre) for roles that need it
    role = user.get("role")
    if role in ("decano", "coordinador"):
        if user.get("facultad_id"):
            fac = await db.facultades.find_one({"id": user["facultad_id"]}, {"_id": 0, "nombre": 1})
            user["facultad_nombre"] = (fac or {}).get("nombre")
        if user.get("programa_id"):
            prog = await db.programas.find_one({"id": user["programa_id"]}, {"_id": 0, "nombre": 1})
            user["programa_nombre"] = (prog or {}).get("nombre")
    return user


def require_roles(*roles):
    async def _checker(user=Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Permiso denegado")
        return user
    return _checker
