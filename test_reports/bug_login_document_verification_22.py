"""Focused verification for login-by-document bug.

Checks:
- API login accepts a numeric cédula and traditional email credentials.
- Served /login document includes no-cache meta tags.
- Browser login page renders Usuario + type=text and allows document login
  without native HTML5 email validation.
"""

import asyncio
import json
import os
import time
from pathlib import Path

import requests


BASE_URL = os.environ.get("TEST_BASE_URL", "https://university-insights.preview.emergentagent.com").rstrip("/")
OUT = Path("/app/test_reports/bug_login_document_verification_22_results.json")


def record(results, name, ok, details=None):
    results["checks"].append({"name": name, "ok": bool(ok), "details": details or {}})


def api_checks(results):
    session = requests.Session()
    for name, payload in [
        ("document_login_api", {"email": "1128441439", "password": "1128441439"}),
        ("superadmin_email_login_api", {"email": "lcorreaq@gmail.com", "password": "IUDigital2026"}),
    ]:
        started = time.time()
        resp = session.post(f"{BASE_URL}/api/auth/login", json=payload, timeout=30)
        elapsed_ms = int((time.time() - started) * 1000)
        body = None
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:300]}
        sanitized = {
            "status_code": resp.status_code,
            "elapsed_ms": elapsed_ms,
            "has_access_token": bool(body.get("access_token")) if isinstance(body, dict) else False,
            "user_role": body.get("user", {}).get("role") if isinstance(body, dict) else None,
            "must_change_password": body.get("user", {}).get("must_change_password") if isinstance(body, dict) else None,
            "documento": body.get("user", {}).get("documento") if isinstance(body, dict) else None,
            "detail": body.get("detail") if isinstance(body, dict) else None,
        }
        ok = resp.status_code == 200 and sanitized["has_access_token"]
        if name == "document_login_api":
            ok = ok and sanitized["documento"] == "1128441439"
        record(results, name, ok, sanitized)

    html_resp = session.get(f"{BASE_URL}/login", timeout=30)
    html = html_resp.text
    record(
        results,
        "login_index_has_no_cache_meta",
        html_resp.status_code == 200
        and 'http-equiv="Cache-Control"' in html
        and "no-cache" in html
        and 'http-equiv="Pragma"' in html
        and 'http-equiv="Expires"' in html,
        {
            "status_code": html_resp.status_code,
            "has_cache_control_meta": 'http-equiv="Cache-Control"' in html and "no-cache" in html,
            "has_pragma_meta": 'http-equiv="Pragma"' in html,
            "has_expires_meta": 'http-equiv="Expires"' in html,
        },
    )


async def browser_checks(results):
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        record(results, "playwright_import", False, {"error": repr(exc)})
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        console_messages = []
        request_failures = []
        login_responses = []
        page.on("console", lambda msg: console_messages.append({"type": msg.type, "text": msg.text[:300]}))
        page.on("requestfailed", lambda req: request_failures.append({"url": req.url, "failure": req.failure.error_text if req.failure else "unknown"}))

        async def on_response(resp):
            if "/api/auth/login" in resp.url:
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                login_responses.append(
                    {
                        "url": resp.url,
                        "status": resp.status,
                        "has_access_token": bool(data.get("access_token")) if isinstance(data, dict) else False,
                        "role": data.get("user", {}).get("role") if isinstance(data, dict) else None,
                        "must_change_password": data.get("user", {}).get("must_change_password") if isinstance(data, dict) else None,
                        "detail": data.get("detail") if isinstance(data, dict) else None,
                    }
                )

        page.on("response", on_response)

        try:
            await context.clear_cookies()
            await page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=60000)
            await page.evaluate("localStorage.clear(); sessionStorage.clear();")
            # Fresh page navigation (not hard reload) after clearing client state.
            await page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=60000)

            labels = [txt.strip() for txt in await page.locator("form label").all_inner_texts()]
            input_locator = page.get_by_test_id("login-email-input")
            password_locator = page.get_by_test_id("login-password-input")
            submit_locator = page.get_by_test_id("login-submit-button")
            type_attr = await input_locator.get_attribute("type")
            placeholder = await input_locator.get_attribute("placeholder")
            validation = await input_locator.evaluate(
                """(el) => {
                    el.value = '1128441439';
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    return {
                        type: el.getAttribute('type'),
                        browserType: el.type,
                        valid: el.checkValidity(),
                        typeMismatch: el.validity.typeMismatch,
                        validationMessage: el.validationMessage
                    };
                }"""
            )
            dom_ok = "Usuario" in labels and "CORREO INSTITUCIONAL" not in " ".join(labels).upper() and type_attr == "text" and validation.get("valid") and not validation.get("typeMismatch") and not validation.get("validationMessage")
            record(
                results,
                "login_dom_usuario_type_text_no_email_validation",
                dom_ok,
                {"labels": labels, "type_attr": type_attr, "placeholder": placeholder, "validation": validation},
            )

            await input_locator.fill("1128441439")
            await password_locator.fill("1128441439")
            await submit_locator.click()
            await page.wait_for_timeout(2500)
            final_url = page.url
            visible_text = await page.locator("body").inner_text(timeout=10000)
            email_validation_symptoms = [
                "Incluye @",
                "falta un símbolo @",
                "Please include an '@'",
                "missing an '@'",
            ]
            invalid_credential_symptoms = ["Credenciales inválidas", "Error de inicio de sesión"]
            bad_symptoms = [s for s in email_validation_symptoms + invalid_credential_symptoms if s in visible_text]
            successful_route = final_url.endswith("/change-password") or final_url.endswith("/mi-panel") or "/change-password" in final_url or "/mi-panel" in final_url
            login_api_ok = any(r.get("status") == 200 and r.get("has_access_token") for r in login_responses)
            record(
                results,
                "document_login_browser_flow",
                successful_route and login_api_ok and not bad_symptoms,
                {
                    "final_url": final_url,
                    "successful_route": successful_route,
                    "login_responses": login_responses,
                    "bad_symptoms": bad_symptoms,
                    "body_text_excerpt": visible_text[:700],
                    "request_failures": request_failures[:10],
                    "console_errors": [m for m in console_messages if m["type"] in ("error", "warning")][:10],
                },
            )
        finally:
            await browser.close()


async def main():
    results = {"base_url": BASE_URL, "checks": []}
    api_checks(results)
    await browser_checks(results)
    results["all_ok"] = all(check["ok"] for check in results["checks"])
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    if not results["all_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())