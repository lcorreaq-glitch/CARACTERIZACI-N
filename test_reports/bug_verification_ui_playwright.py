"""Playwright script body used with mcp_browser_automation for UI verification."""

try:
    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.evaluate("localStorage.clear()")
    await page.goto("https://university-insights.preview.emergentagent.com/login", wait_until="networkidle")
    await page.locator('[data-testid="login-email-input"]').fill('lcorreaq@gmail.com')
    await page.locator('[data-testid="login-password-input"]').fill('IUDigital2026')
    await page.locator('[data-testid="login-submit-button"]').click()
    await page.wait_for_url('**/', timeout=30000)
    await page.locator('[data-testid="executive-dashboard"]').wait_for(timeout=30000)
    p2025_norm = (await page.locator('[data-testid="periodo-2025-2"]').inner_text()).lower()
    p2026_norm = (await page.locator('[data-testid="periodo-2026-1"]').inner_text()).lower()
    assert 'periodo 2025-2' in p2025_norm and '84.871 notas registradas' in p2025_norm and '3.45' in p2025_norm and '76% aprobación' in p2025_norm
    assert 'periodo 2026-1' in p2026_norm and '84.505 notas registradas' in p2026_norm and '3.12' in p2026_norm and '69% aprobación' in p2026_norm
    kpi_text = await page.locator('[data-testid="executive-dashboard"]').inner_text()
    for expected in ['16.461', '14.244 matriculados', '1.918', '4.852', '2.853', '202']:
        assert expected in kpi_text, f'Missing executive KPI text {expected}'
    await page.goto('https://university-insights.preview.emergentagent.com/academico', wait_until='networkidle')
    await page.locator('[data-testid="academic-dashboard"]').wait_for(timeout=30000)
    await page.wait_for_timeout(2000)
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    await page.wait_for_timeout(1000)
    academic_text = await page.locator('[data-testid="academic-dashboard"]').inner_text()
    academic_norm = academic_text.lower()
    for expected in ['promedio por facultad', 'facultades · 2025-2 vs 2026-1', '2025-2:', '2026-1:', 'facultad de ciencias económicas', 'facultad de ciencias y humanidades', 'facultad de ingeniería', 'facultad de educación', 'sin facultad asignada']:
        assert expected in academic_norm, f'Missing academic text {expected}'
    line_info = await page.evaluate("""() => {
        const nodes = Array.from(document.querySelectorAll('[data-testid="academic-dashboard"] svg *'));
        return {
          green: nodes.filter(el => (el.getAttribute('stroke') || '').toLowerCase() === '#059669').length,
          red: nodes.filter(el => (el.getAttribute('stroke') || '').toLowerCase() === '#e3000f').length,
          svgCount: document.querySelectorAll('[data-testid="academic-dashboard"] svg').length
        };
    }""")
    assert line_info['green'] >= 1 and line_info['red'] >= 1, 'Missing green/red period line strokes in academic chart'
except Exception:
    await page.screenshot(path='/app/test_reports/ui_bug_verify/failure_saved_script.jpg', quality=40, full_page=False)
    raise