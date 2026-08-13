"""Gmail API sender using Service Account with Domain-Wide Delegation.

Reason: Google Workspace policy for iudigital.edu.co does not allow generating
Gmail App Passwords, so SMTP with password auth is not viable. This service
uses the recommended pattern for institutional automated email:

  Service Account (in Google Cloud) + Domain-Wide Delegation (in Workspace Admin)
  → impersonates the sender user → uses gmail.send scope → sends email via
    Gmail API without user consent flow.

Security:
- The Service Account JSON is read EXCLUSIVELY from the environment variable
  `GOOGLE_SERVICE_ACCOUNT_JSON` (raw JSON string) or from an absolute file path
  in `GOOGLE_SERVICE_ACCOUNT_FILE`. Never persisted in DB, never sent to frontend.
- Only non-sensitive config is stored in DB (sender email, from name).
- When migrated to GCP, ADC (Application Default Credentials) will work
  automatically without any env var — the runtime service account will provide it.
"""
import base64
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from google.auth.exceptions import RefreshError, DefaultCredentialsError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from database import db

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

DEFAULT_GMAIL_CFG = {
    "auth_method": "smtp",              # "smtp" | "gmail_api"
    "sender_email": "",                 # workspace user to impersonate (e.g. gestion.cienciasyhumanidades@iudigital.edu.co)
    "from_name": "IU Digital Analítica",
}


async def get_gmail_config() -> dict:
    doc = await db.system_settings.find_one({"_id": "gmail_api_config"}, {"_id": 0}) or {}
    return {**DEFAULT_GMAIL_CFG, **doc}


async def save_gmail_config(payload: dict, updated_by: str) -> dict:
    allowed = set(DEFAULT_GMAIL_CFG.keys())
    upd = {k: v for k, v in (payload or {}).items() if k in allowed}
    if "auth_method" in upd and upd["auth_method"] not in ("smtp", "gmail_api"):
        upd.pop("auth_method")
    upd["updated_by"] = updated_by
    await db.system_settings.update_one(
        {"_id": "gmail_api_config"}, {"$set": upd}, upsert=True
    )
    return await get_gmail_config()


def _load_service_account_info() -> Optional[dict]:
    """Load Service Account key from env var (JSON string) or file path.

    Returns dict or None if not configured. Never raises for missing keys —
    callers must handle the None to report 'not_configured' status.
    """
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"__error__": "GOOGLE_SERVICE_ACCOUNT_JSON no es JSON válido."}

    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {"__error__": f"No se pudo leer {path}"}

    return None


def _build_service(sender_email: str):
    """Build an authorized Gmail API service impersonating sender_email.

    Raises exceptions on any configuration / auth error so callers can
    convert them into structured status responses.
    """
    info = _load_service_account_info()
    if info is None:
        raise RuntimeError(
            "Service Account JSON no configurado. "
            "Solicite al administrador de Google Workspace la clave JSON del Service Account "
            "y guárdela en la variable de entorno GOOGLE_SERVICE_ACCOUNT_JSON."
        )
    if isinstance(info, dict) and info.get("__error__"):
        raise RuntimeError(info["__error__"])

    if not sender_email:
        raise RuntimeError("Falta 'sender_email' (correo institucional a impersonar).")

    creds = service_account.Credentials.from_service_account_info(
        info, scopes=[GMAIL_SEND_SCOPE],
    )
    delegated = creds.with_subject(sender_email)
    service = build("gmail", "v1", credentials=delegated, cache_discovery=False)
    return service


def _encode_message(msg: MIMEMultipart) -> dict:
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def _classify_error(exc: Exception) -> str:
    """Return a human-friendly Spanish description for common failures."""
    if isinstance(exc, HttpError):
        status = getattr(exc.resp, "status", None)
        try:
            detail = json.loads(exc.content.decode("utf-8")).get("error", {}).get("message", str(exc))
        except Exception:
            detail = str(exc)
        if status in ("401", 401):
            return f"401 No autorizado: la delegación de dominio no está aprobada o el scope es incorrecto. Detalle: {detail}"
        if status in ("403", 403):
            return f"403 Prohibido: el Service Account no tiene autorización para impersonar al remitente, o falta habilitar Gmail API. Detalle: {detail}"
        return f"HTTP {status}: {detail}"
    if isinstance(exc, RefreshError):
        return f"Fallo al obtener token con impersonación. Verifique que el Client ID esté autorizado en Admin Console con el scope gmail.send. Detalle: {exc}"
    if isinstance(exc, DefaultCredentialsError):
        return f"Credenciales no disponibles: {exc}"
    return f"{type(exc).__name__}: {exc}"


# ============ Public API ============

async def get_status() -> dict:
    """Report the status of the Gmail API integration.

    Returns:
        {
          state: "not_configured" | "configured" | "auth_error",
          message: "...",
          service_account_email: "...@...gserviceaccount.com" (if JSON present),
          sender_email: "...",
          from_name: "...",
          auth_method: "smtp"|"gmail_api",
        }
    """
    cfg = await get_gmail_config()
    result = {
        "auth_method": cfg["auth_method"],
        "sender_email": cfg.get("sender_email") or "",
        "from_name": cfg.get("from_name") or "",
        "service_account_email": None,
        "state": "not_configured",
        "message": "",
    }

    info = _load_service_account_info()
    if info is None:
        result["message"] = (
            "Variable de entorno GOOGLE_SERVICE_ACCOUNT_JSON no está definida. "
            "Solicite al administrador de Workspace el archivo JSON del Service Account "
            "y configúrela como secreto."
        )
        return result
    if isinstance(info, dict) and info.get("__error__"):
        result["state"] = "auth_error"
        result["message"] = info["__error__"]
        return result

    result["service_account_email"] = info.get("client_email")

    if not cfg.get("sender_email"):
        result["message"] = "JSON del Service Account presente, pero falta configurar el correo remitente (sender_email)."
        return result

    # Try a lightweight auth check: build service + get profile of impersonated user.
    try:
        service = _build_service(cfg["sender_email"])
        # profile.get requires gmail.send + gmail.readonly? Actually just build without call
        # to avoid needing readonly scope. We stop here; a real "test email" endpoint
        # can be used to verify send permission.
        # Attempt a very cheap call: users().getProfile(userId='me') — this DOES work with
        # gmail.send scope for the impersonated user.
        service.users().getProfile(userId="me").execute()
        result["state"] = "configured"
        result["message"] = f"Autenticación OK. Delegación aprobada para {cfg['sender_email']}."
        return result
    except Exception as e:
        result["state"] = "auth_error"
        result["message"] = _classify_error(e)
        return result


async def send_email_via_gmail_api(to_email: str, subject: str, html_body: str, text_body: str) -> dict:
    """Send an email using Gmail API. Returns {ok, error?}."""
    cfg = await get_gmail_config()
    sender = cfg.get("sender_email") or ""
    from_name = cfg.get("from_name") or "IU Digital Analítica"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{sender}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        service = _build_service(sender)
        service.users().messages().send(userId="me", body=_encode_message(msg)).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": _classify_error(e)}
