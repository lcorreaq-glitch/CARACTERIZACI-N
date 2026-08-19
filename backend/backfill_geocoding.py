"""Backfill de georreferenciación con lookup (nombre + departamento).

Corrige estudiantes que fueron mal ubicados por el bug del lookup antiguo
(solo por nombre). Lee el CSV original de caracterización, resuelve cada
municipio con el departamento REAL del estudiante y actualiza los campos
geográficos en Mongo:

- ciudad_codigo  (DANE)
- ciudad_nombre  (canónico del catálogo)
- departamento   (canónico del catálogo, respetando el registrado si es país
                  extranjero)
- lat, lon

Ejecutar:
    cd /app/backend
    python3 backfill_geocoding.py             # dry-run (solo reporta)
    python3 backfill_geocoding.py --apply     # aplica cambios
"""
import asyncio
import sys
import unicodedata
from collections import Counter

import pandas as pd

from database import db
from divipola import lookup as divipola_lookup

CSV_PATH = "/app/uploads_user/carac.xlsx"


def _norm(s):
    if pd.isna(s):
        return ""
    s = str(s).strip()
    return s


def _norm_up(s):
    if pd.isna(s):
        return ""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


async def backfill(apply: bool = False):
    print(f"→ Leyendo {CSV_PATH} …")
    df = pd.read_excel(CSV_PATH)
    print(f"  {len(df):,} filas")

    # Columnas relevantes — buscar id del estudiante (cédula) y campos geo
    col_cedula = "doc_estudiante"
    col_ciudad = "Ciudad/Municipio residencia"
    col_depto = "Departamento residencia"
    col_pais = "País residencia"
    for c in (col_cedula, col_ciudad, col_depto):
        if c not in df.columns:
            print(f"❌ Falta columna: {c}. Cols disponibles: {list(df.columns)[:20]}")
            return

    # Índice de estudiantes actualmente en BD
    current = {}
    async for s in db.students.find({}, {"_id": 0, "cedula": 1, "ciudad_codigo": 1,
                                          "ciudad_nombre": 1, "departamento": 1,
                                          "lat": 1, "lon": 1, "pais": 1}):
        current[str(s.get("cedula") or "").strip()] = s

    print(f"  {len(current):,} estudiantes en BD")

    updates = []
    stats = Counter()
    ambiguous = Counter()
    corrections_by_muni = Counter()

    for _, row in df.iterrows():
        cedula = str(_norm(row.get(col_cedula))).strip()
        if not cedula or cedula not in current:
            continue

        ciudad = _norm(row.get(col_ciudad))
        depto = _norm(row.get(col_depto))
        pais = _norm(row.get(col_pais)) or "COLOMBIA"

        if not ciudad:
            stats["sin_ciudad"] += 1
            continue

        muni = divipola_lookup(name=ciudad, departamento=depto)
        if not muni:
            # Intento sin depto (por si es única coincidencia)
            muni = divipola_lookup(name=ciudad)
        if not muni:
            ambiguous[f"{ciudad} · {depto or 'sin depto'}"] += 1
            stats["no_encontrado"] += 1
            continue

        cur = current[cedula]
        # ¿Hay algo que cambiar?
        needs_update = (
            cur.get("ciudad_codigo") != muni["codigo"] or
            (cur.get("lat") or 0) != muni["lat"] or
            (cur.get("lon") or 0) != muni["lon"] or
            _norm_up(cur.get("departamento")) != _norm_up(muni["departamento"])
        )

        if needs_update:
            old_key = f"{cur.get('ciudad_nombre')} ({cur.get('departamento')})"
            new_key = f"{muni['nombre'].title()} ({muni['departamento'].title()})"
            corrections_by_muni[(old_key, new_key)] += 1
            updates.append({
                "cedula": cedula,
                "set": {
                    "ciudad_codigo": muni["codigo"],
                    "ciudad_nombre": muni["nombre"].title(),
                    "departamento": muni["departamento"].title(),
                    "departamento_codigo": muni["codigo"][:2],
                    "lat": muni["lat"],
                    "lon": muni["lon"],
                }
            })
            stats["corregidos"] += 1
        else:
            stats["sin_cambio"] += 1

    print()
    print("=" * 68)
    print(f"Corregibles:   {stats['corregidos']:,}")
    print(f"Sin cambio:    {stats['sin_cambio']:,}")
    print(f"Sin ciudad:    {stats['sin_ciudad']:,}")
    print(f"No encontrado: {stats['no_encontrado']:,}")
    print("=" * 68)
    print()

    # Top de correcciones
    if corrections_by_muni:
        print("Top 15 correcciones (antes → después):")
        for (old, new), n in corrections_by_muni.most_common(15):
            print(f"  {n:>4} · {old}  →  {new}")
        print()

    if ambiguous:
        print("Municipios no resueltos (top 10):")
        for k, v in ambiguous.most_common(10):
            print(f"  {v:>4} · {k}")
        print()

    if not apply:
        print("⚠  DRY-RUN — usa --apply para persistir los cambios.")
        return

    if not updates:
        print("Nada que actualizar.")
        return

    print(f"→ Aplicando {len(updates):,} updates en Mongo…")
    # bulk write en lotes de 500
    from pymongo import UpdateOne
    ops = [UpdateOne({"cedula": u["cedula"]}, {"$set": u["set"]}) for u in updates]
    BATCH = 500
    total_mod = 0
    for i in range(0, len(ops), BATCH):
        res = await db.students.bulk_write(ops[i:i + BATCH], ordered=False)
        total_mod += res.modified_count
        print(f"  lote {i//BATCH + 1}: +{res.modified_count} modificados")
    print(f"✓ Total modificados: {total_mod:,}")


if __name__ == "__main__":
    asyncio.run(backfill(apply="--apply" in sys.argv))
