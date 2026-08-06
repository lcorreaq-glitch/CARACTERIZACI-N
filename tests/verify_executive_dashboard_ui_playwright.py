"""Focused Playwright UI check for executive dashboard bug.

Run inside the browser automation harness with an async Playwright `page` object.
This mirrors the executed UI verification: login, confirm Rural KPI 3.404 and the
new executive dashboard chart cards are visible.
"""


async def run(page):
    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.goto("https://university-insights.preview.emergentagent.com/login")
    await page.wait_for_load_state("networkidle")
    await page.locator('[data-testid="login-email-input"]').fill("lcorreaq@gmail.com")
    await page.locator('[data-testid="login-password-input"]').fill("IUDigital2026")
    await page.locator('[data-testid="login-submit-button"]').click()
    await page.wait_for_url("**/", timeout=30000)
    await page.wait_for_selector('[data-testid="executive-dashboard"]', timeout=30000)
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(1500)

    rural_text = await page.locator('[data-testid="kpi-estudiantes-rurales"]').inner_text()
    assert "3.404" in rural_text, f"Expected Rural KPI 3.404, got {rural_text}"

    for title in [
        "Grupos etarios",
        "Tipo de vulnerabilidad",
        "Georeferenciación · departamento de residencia",
        "Tipo de ubicación",
    ]:
        locator = page.get_by_text(title, exact=True).first
        await locator.scroll_into_view_if_needed()
        await locator.wait_for(timeout=10000)
        assert await locator.is_visible(), f"Expected chart title visible: {title}"

    body_text = await page.locator("body").inner_text()
    for expected_text in ["Víctima conflicto", "Afro", "Indígena", "ANTIOQUIA"]:
        assert expected_text in body_text, f"Expected dashboard text not found: {expected_text}"