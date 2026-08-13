"""Email service for sending credentials via Gmail SMTP.
Reads SMTP config from db.system_settings (key `smtp_config`).
Config keys:
  - smtp_host (default: smtp.gmail.com)
  - smtp_port (default: 587)
  - smtp_user (Gmail address)
  - smtp_password (Gmail App Password — 16 chars)
  - smtp_from_name (display name, e.g. "IU Digital Analítica")
  - smtp_enabled (bool)
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import db


DEFAULT_SMTP = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from_name": "IU Digital Analítica",
    "smtp_enabled": False,
}


async def get_smtp_config() -> dict:
    doc = await db.system_settings.find_one({"_id": "smtp_config"}, {"_id": 0}) or {}
    return {**DEFAULT_SMTP, **doc}


async def save_smtp_config(payload: dict, updated_by: str) -> dict:
    allowed = set(DEFAULT_SMTP.keys())
    upd = {k: v for k, v in (payload or {}).items() if k in allowed}
    if "smtp_port" in upd:
        try:
            upd["smtp_port"] = int(upd["smtp_port"])
        except Exception:
            upd["smtp_port"] = 587
    if "smtp_enabled" in upd:
        upd["smtp_enabled"] = bool(upd["smtp_enabled"])
    upd["updated_by"] = updated_by
    await db.system_settings.update_one(
        {"_id": "smtp_config"}, {"$set": upd}, upsert=True
    )
    return await get_smtp_config()


def _build_credentials_html(full_name: str, email: str, password: str, login_url: str, from_name: str) -> str:
    return f"""<!DOCTYPE html>
<html><body style="font-family:Arial,Helvetica,sans-serif;background:#f4f5f7;padding:24px;color:#111">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:6px;overflow:hidden;border:1px solid #e5e7eb">
    <div style="background:#0033A0;padding:20px 24px;color:#fff">
      <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;opacity:.9">IU Digital · Analítica</div>
      <div style="font-size:22px;font-weight:800;margin-top:6px">Sus credenciales de acceso</div>
    </div>
    <div style="padding:24px">
      <p style="font-size:14px;line-height:1.55;color:#374151">Estimado(a) <b>{full_name}</b>,</p>
      <p style="font-size:14px;line-height:1.55;color:#374151">
        Se ha creado su cuenta en el sistema institucional de analítica académica IU Digital.
        A continuación encontrará sus credenciales temporales.
        <b>Debe cambiar la contraseña en el primer ingreso.</b>
      </p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0;background:#f9fafb;border-radius:4px">
        <tr><td style="padding:10px 14px;color:#6b7280;font-size:12px;width:120px">Correo</td>
            <td style="padding:10px 14px;font-family:monospace;font-size:13px"><b>{email}</b></td></tr>
        <tr><td style="padding:10px 14px;color:#6b7280;font-size:12px">Contraseña</td>
            <td style="padding:10px 14px;font-family:monospace;font-size:13px"><b>{password}</b></td></tr>
      </table>
      <p style="text-align:center;margin:22px 0">
        <a href="{login_url}" style="background:#0033A0;color:#fff;text-decoration:none;padding:12px 28px;border-radius:4px;font-weight:600;font-size:14px;display:inline-block">
          Ingresar al sistema
        </a>
      </p>
      <p style="font-size:12px;color:#6b7280;line-height:1.55;border-top:1px solid #e5e7eb;padding-top:16px;margin-top:24px">
        Si no esperaba este correo, por favor contacte al administrador del sistema.
        Este es un mensaje automático, no responda directamente.
      </p>
      <p style="font-size:11px;color:#9ca3af;margin-top:12px">— {from_name}</p>
    </div>
  </div>
</body></html>"""


async def send_credentials_email(to_email: str, full_name: str, password: str, login_url: str) -> dict:
    """Envía correo con credenciales. Enruta según el método de autenticación configurado
    (SMTP legacy o Gmail API con Service Account). Retorna {ok, error?}."""
    # Import local para evitar import circular (gmail_api_service importa db)
    from gmail_api_service import get_gmail_config, send_email_via_gmail_api

    gmail_cfg = await get_gmail_config()
    auth_method = gmail_cfg.get("auth_method", "smtp")

    from_name = gmail_cfg.get("from_name") or "IU Digital Analítica"
    html_body = _build_credentials_html(full_name, to_email, password, login_url, from_name)
    text_body = (
        f"Estimado(a) {full_name},\n\n"
        f"Se ha creado su cuenta en IU Digital Analítica.\n"
        f"Correo: {to_email}\n"
        f"Contraseña temporal: {password}\n\n"
        f"Ingrese en: {login_url}\n"
        f"Debe cambiar la contraseña en el primer acceso.\n\n"
        f"— {from_name}"
    )
    subject = "Sus credenciales de acceso · IU Digital Analítica"

    if auth_method == "gmail_api":
        return await send_email_via_gmail_api(to_email, subject, html_body, text_body)

    # ---- SMTP legacy path ----
    return await _send_via_smtp(to_email, subject, from_name, html_body, text_body)


async def _send_via_smtp(to_email: str, subject: str, from_name: str, html_body: str, text_body: str) -> dict:
    cfg = await get_smtp_config()
    if not cfg.get("smtp_enabled"):
        return {"ok": False, "error": "SMTP no está habilitado en Configuración."}
    if not cfg.get("smtp_user") or not cfg.get("smtp_password"):
        return {"ok": False, "error": "Faltan credenciales SMTP (usuario/contraseña de aplicación)."}

    from_email = cfg["smtp_user"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"]), timeout=20) as server:
            server.starttls(context=context)
            server.login(cfg["smtp_user"], cfg["smtp_password"])
            server.sendmail(from_email, [to_email], msg.as_string())
        return {"ok": True}
    except smtplib.SMTPAuthenticationError as e:
        return {"ok": False, "error": f"Autenticación fallida: verifique correo/App Password. Detalle: {e.smtp_code}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


async def send_test_email(to_email: str) -> dict:
    """Envío rápido para probar la configuración de correo (SMTP o Gmail API)."""
    from gmail_api_service import get_gmail_config, send_email_via_gmail_api

    gmail_cfg = await get_gmail_config()
    auth_method = gmail_cfg.get("auth_method", "smtp")
    from_name = gmail_cfg.get("from_name") or "IU Digital Analítica"

    subject = "Prueba de correo · IU Digital Analítica"
    html = (
        f"<div style='font-family:Arial;padding:20px'>"
        f"<h2 style='color:#0033A0'>✓ Prueba de envío exitosa</h2>"
        f"<p>Este correo confirma que la configuración de <b>{from_name}</b> funciona correctamente.</p>"
        f"<p style='font-size:12px;color:#6b7280'>Método: <b>{auth_method}</b></p></div>"
    )
    text = f"Prueba de envío exitosa desde IU Digital Analítica. Método: {auth_method}."

    if auth_method == "gmail_api":
        return await send_email_via_gmail_api(to_email, subject, html, text)

    # SMTP legacy path
    cfg = await get_smtp_config()
    if not cfg.get("smtp_enabled"):
        return {"ok": False, "error": "SMTP no está habilitado."}
    if not cfg.get("smtp_user") or not cfg.get("smtp_password"):
        return {"ok": False, "error": "Faltan credenciales SMTP."}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{cfg['smtp_user']}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"]), timeout=20) as server:
            server.starttls(context=context)
            server.login(cfg["smtp_user"], cfg["smtp_password"])
            server.sendmail(cfg["smtp_user"], [to_email], msg.as_string())
        return {"ok": True}
    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "error": "Autenticación fallida. Revise que use un App Password (no la contraseña normal de Gmail)."}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
