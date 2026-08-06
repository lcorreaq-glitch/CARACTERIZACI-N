#!/usr/bin/env python3
"""Focused Playwright UI regression for executive dashboard promedio KPI."""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright, expect


def frontend_url() -> str:
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().strip('"')
    return "http://localhost:3000"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            await page.goto(frontend_url(), wait_until="domcontentloaded")
            await page.evaluate("localStorage.clear()")
            await page.goto(f"{frontend_url().rstrip('/')}/login", wait_until="domcontentloaded")
            await page.get_by_test_id("login-email-input").fill("lcorreaq@gmail.com")
            await page.get_by_test_id("login-password-input").fill("IUDigital2026")
            await page.get_by_test_id("login-submit-button").click()
            await expect(page.get_by_test_id("executive-dashboard")).to_be_visible(timeout=30000)

            promedio_card = page.get_by_test_id("kpi-promedio-general")
            await expect(promedio_card).to_be_visible(timeout=15000)
            promedio_text = await promedio_card.inner_text()
            assert "3.29" in promedio_text, f"Promedio general card did not show 3.29: {promedio_text}"
            assert "3.80" not in promedio_text, f"Promedio general card still showed 3.80: {promedio_text}"

            periodo_2025 = page.get_by_test_id("periodo-2025-2")
            periodo_2026 = page.get_by_test_id("periodo-2026-1")
            await expect(periodo_2025).to_be_visible(timeout=15000)
            await expect(periodo_2026).to_be_visible(timeout=15000)
            text_2025 = await periodo_2025.inner_text()
            text_2026 = await periodo_2026.inner_text()
            assert "3.45" in text_2025, f"Periodo 2025-2 card missing 3.45: {text_2025}"
            assert "3.12" in text_2026, f"Periodo 2026-1 card missing 3.12: {text_2026}"

            for heading in [
                "Grupos etarios",
                "Tipo de vulnerabilidad",
                "Georeferenciación · departamento de residencia",
                "Tipo de ubicación",
            ]:
                await expect(page.get_by_text(heading, exact=True)).to_be_visible(timeout=10000)
            print("UI regression passed")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())