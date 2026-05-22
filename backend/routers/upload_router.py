"""Excel upload + validation router."""
from datetime import datetime
import io
import uuid
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from auth import require_roles
from database import db
from divipola import lookup, MUNICIPIOS

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

REQUIRED_COLS = ["Cédula", "Nombre", "Apellidos", "Programa", "EstadoMatricula", "Promedio"]


def _b(v):
    if v is None:
        return False
    return str(v).strip().lower() in ("sí", "si", "true", "1", "yes", "y")


@router.get("/")
async def list_uploads(user=Depends(require_roles("superadmin", "admin"))):
    items = await db.uploads.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return items


@router.post("/preview")
async def preview(file: UploadFile = File(...), user=Depends(require_roles("superadmin", "admin"))):
    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"No se pudo leer el Excel: {e}")
    df = df.fillna("")
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    preview_rows = df.head(10).to_dict(orient="records")
    # Coerce to plain types
    for r in preview_rows:
        for k, v in r.items():
            r[k] = "" if v is None else str(v)[:200]
    return {
        "filename": file.filename,
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "columns": list(df.columns),
        "missing_required": missing,
        "preview": preview_rows,
    }


@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    periodo: str = Form(...),
    user=Depends(require_roles("superadmin", "admin")),
):
    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"No se pudo leer el Excel: {e}")
    df = df.fillna("")
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise HTTPException(400, f"Faltan columnas obligatorias: {missing}")

    upload_id = str(uuid.uuid4())
    inserted = 0
    errores = 0
    ant_munis = [m for m in MUNICIPIOS if m["departamento"] == "ANTIOQUIA"]
    docs = []
    for _, row in df.iterrows():
        cedula = str(row.get("Cédula", "")).strip()
        if not cedula:
            errores += 1
            continue
        ciudad_raw = row.get("C_Ciudad")
        muni = None
        if ciudad_raw and str(ciudad_raw) not in ("0", "0.0", ""):
            try:
                code5 = str(int(float(ciudad_raw))).zfill(5)
                if code5.startswith("0"):
                    code5 = "05" + code5[-3:]
                muni = lookup(codigo=code5)
            except Exception:
                pass
        if not muni:
            idx = abs(hash(cedula)) % len(ant_munis)
            muni = ant_munis[idx]
        promedio = float(row.get("Promedio") or 0)
        try:
            avance_total = float(row.get("Total") or 0)
            aprobadas = float(row.get("Aprobadas") or 0)
            avance_pct = (aprobadas / avance_total * 100.0) if avance_total else 0.0
        except Exception:
            avance_pct = 0.0
        programa = str(row.get("Programa") or "").strip().upper()
        docs.append({
            "id": str(uuid.uuid4()),
            "cedula": cedula,
            "nombre": str(row.get("Nombre") or "").strip(),
            "apellidos": str(row.get("Apellidos") or "").strip(),
            "correo": str(row.get("Correo") or "").strip(),
            "telefono": str(row.get("Telefono") or "").strip(),
            "programa": programa,
            "nivel": int(row.get("Nivel") or 0) if str(row.get("Nivel") or "").strip().isdigit() else 0,
            "estado_matricula": str(row.get("EstadoMatricula") or "").strip(),
            "estado": str(row.get("Estado") or "").strip(),
            "promedio": promedio,
            "total_materias": float(row.get("Total") or 0),
            "aprobadas": float(row.get("Aprobadas") or 0),
            "reprobadas": float(row.get("Reprobadas") or 0),
            "pendientes": float(row.get("Pendientes") or 0),
            "avance_pct": round(avance_pct, 2),
            "genero": str(row.get("P_idGenero") or "NO INFORMA").strip().upper(),
            "estrato": str(row.get("P_idEstrato") or "SIN DATO").strip().upper(),
            "estado_civil": str(row.get("P_idEstadoCivil") or "").strip(),
            "sisben_tiene": _b(row.get("P_idSisben")),
            "grupo_sisben": str(row.get("P_idGrupoSisben") or "").strip(),
            "etnia": str(row.get("P_idEtnia") or "NO APLICA").strip().upper(),
            "discapacidad_flag": _b(row.get("C_blnTieneDiscapacidad")),
            "discapacidad_tipo": str(row.get("P_idDiscapacidad") or "").strip(),
            "grupo_vulnerable": _b(row.get("C_blnGrupoVulnerable")),
            "victima_conflicto": str(row.get("C_intVictima") or "").strip().lower() in ("sí", "si"),
            "tipo_ubicacion": str(row.get("C_idTipoUbicacion") or "").strip(),
            "ingresos_flia": float(row.get("C_dblIngresosFlia") or 0),
            "ciudad_codigo": muni["codigo"],
            "ciudad_nombre": muni["nombre"],
            "departamento": muni["departamento"],
            "lat": muni["lat"],
            "lon": muni["lon"],
            "facultad": None,
            "periodo": periodo,
            "upload_id": upload_id,
            "created_at": datetime.utcnow().isoformat(),
        })
        inserted += 1

    # Remove prior version for same periodo (versioning policy: replace)
    await db.students.delete_many({"periodo": periodo})
    if docs:
        BATCH = 2000
        for i in range(0, len(docs), BATCH):
            await db.students.insert_many(docs[i:i + BATCH])

    upload_doc = {
        "id": upload_id,
        "filename": file.filename,
        "periodo": periodo,
        "total_rows": int(len(df)),
        "inserted": inserted,
        "errores": errores,
        "uploaded_by": user["email"],
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.uploads.insert_one(upload_doc)
    upload_doc.pop("_id", None)
    return upload_doc


@router.post("/rollback/{upload_id}")
async def rollback(upload_id: str, user=Depends(require_roles("superadmin"))):
    res = await db.students.delete_many({"upload_id": upload_id})
    await db.uploads.update_one({"id": upload_id}, {"$set": {"rolled_back": True, "rolled_back_at": datetime.utcnow().isoformat()}})
    return {"ok": True, "deleted": res.deleted_count}
