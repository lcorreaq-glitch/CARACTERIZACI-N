"""Configuration router: SMTP settings, AI provider (Emergent/Gemini), and email dispatch.
Only superadmin can read/write sensitive credentials.
"""
import os
import io
import secrets
import string
from datetime import datetime
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from auth import get_current_user, require_roles, hash_password
from database import db
from email_service import (
    get_smtp_config, save_smtp_config, send_credentials_email, send_test_email,
)

router = APIRouter(prefix="/api/config", tags=["config"])


# --- AI provider settings ---
DEFAULT_AI = {
    "ai_provider": "emergent",   # "emergent" | "gemini_google"
    "gemini_api_key": "",
    "gemini_model": "gemini-2.0-flash",
    "openai_model": "gpt-4o",
    "ai_enabled": True,
}


async def _get_ai_config() -> dict:
    doc = await db.system_settings.find_one({"_id": "ai_config"}, {"_id": 0}) or {}
    return {**DEFAULT_AI, **doc}


def _mask(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) < 8:
        return "•" * len(secret)
    return f"{secret[:4]}{'•' * (len(secret) - 8)}{secret[-4:]}"


# ---------- SMTP ----------
class SMTPPayload(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_name: str | None = None
    smtp_enabled: bool | None = None


@router.get("/smtp")
async def read_smtp(user=Depends(require_roles("superadmin"))):
    cfg = await get_smtp_config()
    return {**cfg, "smtp_password_mask": _mask(cfg.get("smtp_password", ""))}


@router.patch("/smtp")
async def update_smtp(payload: SMTPPayload, user=Depends(require_roles("superadmin"))):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    # Do not overwrite password with empty string
    if data.get("smtp_password") == "":
        data.pop("smtp_password", None)
    cfg = await save_smtp_config(data, updated_by=user.get("email", "?"))
    return {**cfg, "smtp_password_mask": _mask(cfg.get("smtp_password", ""))}


class TestEmailPayload(BaseModel):
    to_email: EmailStr


@router.post("/smtp/test")
async def smtp_test(payload: TestEmailPayload, user=Depends(require_roles("superadmin"))):
    r = await send_test_email(payload.to_email)
    if not r.get("ok"):
        raise HTTPException(400, r.get("error", "Error desconocido"))
    return {"ok": True, "message": f"Correo de prueba enviado a {payload.to_email}"}


# ---------- AI provider ----------
class AIPayload(BaseModel):
    ai_provider: str | None = None  # "emergent" | "gemini_google"
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openai_model: str | None = None
    ai_enabled: bool | None = None


@router.get("/ai")
async def read_ai(user=Depends(require_roles("superadmin"))):
    cfg = await _get_ai_config()
    return {
        **cfg,
        "gemini_api_key_mask": _mask(cfg.get("gemini_api_key", "")),
        "emergent_key_present": bool(os.environ.get("EMERGENT_LLM_KEY")),
    }


@router.patch("/ai")
async def update_ai(payload: AIPayload, user=Depends(require_roles("superadmin"))):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if data.get("gemini_api_key") == "":
        data.pop("gemini_api_key", None)
    if data.get("ai_provider") and data["ai_provider"] not in ("emergent", "gemini_google"):
        raise HTTPException(400, "ai_provider inválido")
    data["updated_by"] = user.get("email")
    data["updated_at"] = datetime.utcnow().isoformat()
    await db.system_settings.update_one({"_id": "ai_config"}, {"$set": data}, upsert=True)
    cfg = await _get_ai_config()
    return {
        **cfg,
        "gemini_api_key_mask": _mask(cfg.get("gemini_api_key", "")),
        "emergent_key_present": bool(os.environ.get("EMERGENT_LLM_KEY")),
    }


# ---------- Send credentials ----------
def _generate_password(length: int = 10) -> str:
    """Contraseña temporal legible (sin caracteres ambiguos)."""
    alphabet = string.ascii_letters + string.digits
    alphabet = alphabet.replace("l", "").replace("I", "").replace("O", "").replace("0", "").replace("1", "")
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _login_url() -> str:
    return os.environ.get("APP_PUBLIC_URL") or "https://university-insights.preview.emergentagent.com"


class SendCredsPayload(BaseModel):
    reset_password: bool = True   # generar nueva contraseña temporal antes de enviar
    only_missing: bool = True     # (bulk) solo envía a docentes que aún no reciben


@router.post("/send-credentials/{user_id}")
async def send_credentials_one(
    user_id: str,
    payload: SendCredsPayload,
    admin=Depends(require_roles("superadmin", "direccion")),
):
    """Envía correo con credenciales a un usuario. Si reset_password=True, genera nueva contraseña temporal.
    IMPORTANTE: primero verifica SMTP y envía el correo. SOLO si el envío es exitoso persiste el reset
    de contraseña. Así nunca deja al usuario bloqueado si el SMTP falla."""
    u = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    if not u.get("email"):
        raise HTTPException(400, "Usuario sin correo")
    if not payload.reset_password:
        raise HTTPException(400, "Solo se puede enviar contraseña recién generada. Use reset_password=true.")

    # Preflight: verificar SMTP habilitado + credenciales antes de tocar la contraseña.
    smtp_cfg = await get_smtp_config()
    if not smtp_cfg.get("smtp_enabled"):
        raise HTTPException(400, "SMTP no está habilitado en Configuración. No se envió ningún correo ni se modificó ninguna contraseña.")
    if not smtp_cfg.get("smtp_user") or not smtp_cfg.get("smtp_password"):
        raise HTTPException(400, "Faltan credenciales SMTP (usuario/App Password). No se envió ningún correo ni se modificó ninguna contraseña.")

    new_password = _generate_password()
    # Intentar enviar PRIMERO (con la contraseña en memoria).
    res = await send_credentials_email(
        to_email=u["email"],
        full_name=u.get("full_name") or u["email"],
        password=new_password,
        login_url=_login_url(),
    )
    if not res.get("ok"):
        # No tocamos la contraseña — el usuario mantiene su acceso previo.
        raise HTTPException(400, f"Fallo al enviar correo: {res.get('error', 'error desconocido')}. La contraseña no fue modificada.")

    # Envío OK → persistir el reset.
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "password": hash_password(new_password),
            "must_change_password": True,
            "credentials_sent_at": datetime.utcnow().isoformat(),
            "credentials_sent_by": admin.get("email"),
        }},
    )
    return {"ok": True, "email": u["email"], "message": "Correo enviado y contraseña actualizada"}


class BulkPayload(BaseModel):
    role: str = "profesor"
    only_missing: bool = True
    limit: int = 200   # tope por invocación para no exceder timeouts


@router.post("/send-credentials-bulk")
async def send_credentials_bulk(
    payload: BulkPayload,
    admin=Depends(require_roles("superadmin")),
):
    """Envía credenciales masivamente. Preflight SMTP: si no está habilitado, no toca nada y devuelve 400.
    Para cada usuario, envía primero y sólo persiste el reset si el envío es exitoso.
    Limitado a `limit` (default 200) por invocación para evitar timeouts del proxy."""
    smtp_cfg = await get_smtp_config()
    if not smtp_cfg.get("smtp_enabled"):
        raise HTTPException(400, "SMTP no está habilitado en Configuración. No se envió ningún correo ni se modificó ninguna contraseña.")
    if not smtp_cfg.get("smtp_user") or not smtp_cfg.get("smtp_password"):
        raise HTTPException(400, "Faltan credenciales SMTP (usuario/App Password). No se envió ningún correo ni se modificó ninguna contraseña.")

    query = {"role": payload.role, "active": True}
    if payload.only_missing:
        query["$or"] = [
            {"credentials_sent_at": {"$exists": False}},
            {"credentials_sent_at": None},
        ]
    users_list = await db.users.find(query, {"_id": 0}).limit(max(1, min(payload.limit, 500))).to_list(500)

    sent, failed = [], []
    for u in users_list:
        if not u.get("email"):
            failed.append({"id": u.get("id"), "error": "sin correo"})
            continue
        pw = _generate_password()
        # Envío PRIMERO — contraseña sólo en memoria hasta confirmar entrega.
        r = await send_credentials_email(
            to_email=u["email"],
            full_name=u.get("full_name") or u["email"],
            password=pw,
            login_url=_login_url(),
        )
        if r.get("ok"):
            await db.users.update_one(
                {"id": u["id"]},
                {"$set": {
                    "password": hash_password(pw),
                    "must_change_password": True,
                    "credentials_sent_at": datetime.utcnow().isoformat(),
                    "credentials_sent_by": admin.get("email"),
                }},
            )
            sent.append({"id": u["id"], "email": u["email"]})
        else:
            failed.append({"id": u["id"], "email": u["email"], "error": r.get("error")})
    return {
        "ok": True,
        "total_target": len(users_list),
        "sent": len(sent),
        "failed": len(failed),
        "sent_list": sent[:200],
        "failed_list": failed[:200],
        "note": f"Procesados {len(users_list)} usuarios en esta llamada. Repita la operación si hay más pendientes.",
    }


# ---------- Overview (safe for direccion; no secrets) ----------
@router.get("/overview")
async def config_overview(user=Depends(require_roles("superadmin", "direccion"))):
    """Vista general no sensible del estado de configuración (para dashboard interno)."""
    smtp = await get_smtp_config()
    ai = await _get_ai_config()
    n_docentes_total = await db.users.count_documents({"role": "profesor", "active": True})
    n_docentes_notified = await db.users.count_documents(
        {"role": "profesor", "active": True, "credentials_sent_at": {"$ne": None}}
    )
    return {
        "smtp_enabled": bool(smtp.get("smtp_enabled")),
        "smtp_from": smtp.get("smtp_user"),
        "ai_provider": ai.get("ai_provider"),
        "ai_enabled": bool(ai.get("ai_enabled")),
        "emergent_key_present": bool(os.environ.get("EMERGENT_LLM_KEY")),
        "gemini_key_present": bool(ai.get("gemini_api_key")),
        "docentes_total": n_docentes_total,
        "docentes_credentials_sent": n_docentes_notified,
    }


# ---------- Reset masivo + descarga listado inicial ----------
class ResetInitialPayload(BaseModel):
    role: str = "profesor"
    strategy: str = "cedula"   # cédula como contraseña inicial


@router.post("/reset-initial-passwords")
async def reset_initial_passwords(
    payload: ResetInitialPayload,
    admin=Depends(require_roles("superadmin")),
):
    """Resetea la contraseña de todos los usuarios del rol a su CÉDULA (documento).
    must_change_password=True. Útil cuando aún no hay correo institucional."""
    users_list = await db.users.find({"role": payload.role, "active": True}, {"_id": 0}).to_list(3000)
    reset, skipped = 0, 0
    for u in users_list:
        ced = (u.get("documento") or u.get("cedula") or "").strip()
        if not ced:
            skipped += 1
            continue
        await db.users.update_one(
            {"id": u["id"]},
            {"$set": {
                "password": hash_password(ced),
                "must_change_password": True,
                "initial_password_is_cedula": True,
                "credentials_reset_by": admin.get("email"),
                "credentials_reset_at": datetime.utcnow().isoformat(),
            }}
        )
        reset += 1
    return {"ok": True, "reset": reset, "skipped_without_cedula": skipped, "total": len(users_list)}


@router.get("/initial-credentials.xlsx")
async def download_initial_credentials(
    role: str = "profesor",
    admin=Depends(require_roles("superadmin")),
):
    """Descarga Excel con nombre, cédula (usuario inicial), correo de contacto y facultad para
    entregar credenciales físicamente cuando aún no hay correo institucional."""
    users_list = await db.users.find({"role": role, "active": True}, {"_id": 0, "password": 0}).to_list(3000)
    rows = []
    for u in users_list:
        ced = (u.get("documento") or u.get("cedula") or "").strip()
        rows.append({
            "Nombre completo": u.get("full_name") or "",
            "Cédula (Usuario)": ced,
            "Contraseña inicial": ced,   # regla: contraseña inicial = cédula
            "Correo de contacto": u.get("email") or u.get("correo_personal") or "",
            "Correo institucional": u.get("correo_institucional") or "",
            "IdDoc": u.get("iddoc") or "",
            "Rol": u.get("role") or "",
            "Cambio obligatorio primer ingreso": "Sí" if u.get("must_change_password") else "No",
            "Estado": "Activo" if u.get("active", True) else "Inactivo",
        })
    df = pd.DataFrame(rows)
    # Forzar todas las columnas a texto para preservar ceros iniciales y evitar "123.0"
    for col in df.columns:
        df[col] = df[col].astype(str).replace({"nan": "", "None": ""})
    df = df.sort_values(by=["Nombre completo"], na_position="last")

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Credenciales iniciales", index=False)
        ws = writer.sheets["Credenciales iniciales"]
        # Ajustar anchos + forzar formato texto en columna Cédula (col B) y Contraseña (col C)
        widths = [40, 16, 20, 30, 30, 12, 14, 26, 12]
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
        # Formato texto explícito para todas las celdas
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.number_format = "@"
    output.seek(0)
    filename = f"credenciales_iniciales_{role}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
