#!/usr/bin/env python3
"""Check whether apparent prueba note rows come directly from uploaded source files."""
import json
from pathlib import Path

import pandas as pd

rows = {}
for label, file in [("2025-2", "/app/uploads_user/notas_25_2.xlsx"), ("2026-file", "/app/uploads_user/notas_26_2.xlsx")]:
    p = Path(file)
    if not p.exists():
        rows[label] = "missing"
        continue
    df = pd.read_excel(p, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]
    match = df[df.get("DOC_ESTUDIANTE").astype(str).str.replace(r"\.0$", "", regex=True) == "292827"]
    rows[label] = match.head(20).to_dict(orient="records")
print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))