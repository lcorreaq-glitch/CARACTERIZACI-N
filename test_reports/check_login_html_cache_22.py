"""Inspect served /login HTML and cache-related response headers."""

import json
import time
from pathlib import Path

import requests

BASE = "https://university-insights.preview.emergentagent.com"
OUT = Path("/app/test_reports/check_login_html_cache_22_results.json")

session = requests.Session()
checks = []
for path in ["/login", f"/login?cache_probe={int(time.time())}"]:
    resp = session.get(
        BASE + path,
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
        timeout=30,
    )
    text = resp.text
    checks.append(
        {
            "path": path,
            "status_code": resp.status_code,
            "response_cache_control": resp.headers.get("cache-control"),
            "response_etag": resp.headers.get("etag"),
            "has_cache_control_meta": 'http-equiv="Cache-Control"' in text and "no-cache" in text,
            "has_pragma_meta": 'http-equiv="Pragma"' in text,
            "has_expires_meta": 'http-equiv="Expires"' in text,
            "title_is_iudigital": "IU Digital · Analítica académica" in text,
            "title_is_old_emergent": "Emergent | Fullstack App" in text,
        }
    )

result = {"base_url": BASE, "checks": checks, "all_have_no_cache_meta": all(c["has_cache_control_meta"] and c["has_pragma_meta"] and c["has_expires_meta"] for c in checks)}
OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))