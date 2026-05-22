"""Excel upload + validation router."""
from datetime import datetime
import io
import uuid
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from auth import require_roles, hash_password
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
    # Realistic Colombia + extranjero distribution for unknown municipality codes
    by_dept = {}
    for m in MUNICIPIOS:
        by_dept.setdefault(m["departamento"], []).append(m)
    _weights = {
        "ANTIOQUIA": 45, "BOGOTA D.C.": 10, "CUNDINAMARCA": 5, "VALLE DEL CAUCA": 8,
        "ATLANTICO": 4, "BOLIVAR": 3, "SANTANDER": 4, "NORTE DE SANTANDER": 2,
        "CORDOBA": 2, "CALDAS": 2, "RISARALDA": 2, "QUINDIO": 1, "TOLIMA": 1, "HUILA": 1,
        "NARIÑO": 1, "CAUCA": 1, "MAGDALENA": 1, "CESAR": 1, "LA GUAJIRA": 1, "SUCRE": 1,
        "BOYACA": 1, "META": 1, "CHOCO": 1, "CASANARE": 1, "VENEZUELA": 1, "ECUADOR": 1,
        "PANAMA": 1, "ESTADOS UNIDOS": 1, "ESPAÑA": 1,
    }
    dept_pool = []
    for dept, w in _weights.items():
        if by_dept.get(dept):
            dept_pool.extend([dept] * w)
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
            h = abs(hash(cedula))
            dept = dept_pool[h % len(dept_pool)]
            mlist = by_dept[dept]
            muni = mlist[(h // 1000) % len(mlist)]
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
            "sisben_nivel": str(row.get("P_idSisben") or "").strip().upper() or "NO APLICA",
            "sisben_tiene": str(row.get("P_idSisben") or "").strip().lower() not in ("", "no aplica", "no", "ninguno", "ninguna"),
            "grupo_sisben": str(row.get("P_idGrupoSisben") or "").strip().upper() or "NO APLICA",
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



# ============================================================================
# Templates de Excel descargables
# ============================================================================

TEMPLATES = {
    "estudiantes": {
        "filename": "plantilla_estudiantes.xlsx",
        "sheet": "Estudiantes",
        "columns": [
            "Cédula", "Nombre", "Apellidos", "Correo", "Telefono",
            "Programa", "Nivel", "EstadoMatricula", "Estado",
            "Promedio", "Total", "Aprobadas", "Reprobadas", "Pendientes",
            "P_idGenero", "P_idEstrato", "P_idEstadoCivil",
            "P_idSisben", "P_idGrupoSisben", "P_idEtnia",
            "C_blnTieneDiscapacidad", "P_idDiscapacidad",
            "C_blnGrupoVulnerable", "C_intVictima",
            "C_idTipoUbicacion", "C_dblIngresosFlia", "C_Ciudad",
        ],
        "sample": [{
            "Cédula": "1234567890", "Nombre": "JUAN", "Apellidos": "PÉREZ GÓMEZ",
            "Correo": "juan.perez@iudigital.edu.co", "Telefono": "3001234567",
            "Programa": "INGENIERÍA DE SOFTWARE Y DATOS", "Nivel": 3,
            "EstadoMatricula": "Estudiante Matriculado", "Estado": "Activo",
            "Promedio": 4.1, "Total": 30, "Aprobadas": 24, "Reprobadas": 1, "Pendientes": 5,
            "P_idGenero": "MASCULINO", "P_idEstrato": "ESTRATO 3", "P_idEstadoCivil": "SOLTERO",
            "P_idSisben": "B2", "P_idGrupoSisben": "GRUPO B", "P_idEtnia": "MESTIZOS",
            "C_blnTieneDiscapacidad": "No", "P_idDiscapacidad": "",
            "C_blnGrupoVulnerable": "No", "C_intVictima": "No",
            "C_idTipoUbicacion": "Urbana", "C_dblIngresosFlia": 2000000, "C_Ciudad": "05001",
        }],
        "instructions": [
            "Una fila por estudiante.",
            "La cédula es OBLIGATORIA y única.",
            "P_idSisben debe ser un nivel válido: A1-A5, B1-B7, C1-C18, D1-D21 o 'NO APLICA'.",
            "C_Ciudad: código DANE de 5 dígitos (ej. 05001 = MEDELLIN). Si no se reconoce, se asigna aleatoriamente.",
            "EstadoMatricula: 'Estudiante Matriculado' para activos.",
            "Booleanos: 'Sí'/'No' o 'true'/'false'.",
        ],
    },
    "notas": {
        "filename": "plantilla_notas.xlsx",
        "sheet": "Notas",
        "columns": [
            "Cedula", "Periodo", "CodigoMateria", "NombreMateria",
            "NombreDocente", "EmailDocente", "Nota", "Aprobada",
        ],
        "sample": [
            {"Cedula": "1234567890", "Periodo": "2025-2", "CodigoMateria": "PRG-01",
             "NombreMateria": "Contabilidad General", "NombreDocente": "Prof. Ana Restrepo",
             "EmailDocente": "ana.restrepo@iudigital.edu.co", "Nota": 4.3, "Aprobada": "Sí"},
            {"Cedula": "1234567890", "Periodo": "2025-2", "CodigoMateria": "PRG-02",
             "NombreMateria": "Microeconomía", "NombreDocente": "Prof. Carlos Vega",
             "EmailDocente": "carlos.vega@iudigital.edu.co", "Nota": 2.9, "Aprobada": "No"},
        ],
        "instructions": [
            "Una fila por nota (estudiante × materia × periodo).",
            "Cedula debe existir en la base de estudiantes.",
            "Si la materia o el docente no existen, se crean automáticamente.",
            "Nota: escala 0.0 a 5.0. Aprobada: 'Sí' si Nota >= 3.0.",
            "Periodo formato 'YYYY-S' (ej. 2025-2).",
        ],
    },
    "docente_materia": {
        "filename": "plantilla_docente_materia.xlsx",
        "sheet": "DocenteMateria",
        "columns": [
            "EmailDocente", "NombreDocente",
            "CodigoMateria", "NombreMateria", "Periodo",
        ],
        "sample": [
            {"EmailDocente": "ana.restrepo@iudigital.edu.co", "NombreDocente": "Prof. Ana Restrepo",
             "CodigoMateria": "PRG-01", "NombreMateria": "Contabilidad General", "Periodo": "2026-1"},
            {"EmailDocente": "carlos.vega@iudigital.edu.co", "NombreDocente": "Prof. Carlos Vega",
             "CodigoMateria": "PRG-02", "NombreMateria": "Microeconomía", "Periodo": "2026-1"},
        ],
        "instructions": [
            "Una fila por relación (docente × materia × periodo).",
            "Si el EmailDocente no existe, se crea automáticamente con rol 'docente' y contraseña inicial 'IUDigital2026!'.",
            "Si la materia no existe (CodigoMateria), se crea con el NombreMateria provisto.",
            "El docente debe cambiar su contraseña en su primer ingreso.",
        ],
    },
}


@router.get("/template/{tipo}")
async def download_template(tipo: str, user=Depends(require_roles("superadmin", "admin"))):
    """Descarga una plantilla Excel vacía con cabeceras y una fila de ejemplo."""
    if tipo not in TEMPLATES:
        raise HTTPException(404, f"Plantilla '{tipo}' no encontrada. Opciones: {list(TEMPLATES.keys())}")
    tpl = TEMPLATES[tipo]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Hoja datos
        df = pd.DataFrame(tpl["sample"], columns=tpl["columns"])
        df.to_excel(writer, sheet_name=tpl["sheet"], index=False)
        # Hoja instrucciones
        inst = pd.DataFrame({"Instrucciones": tpl["instructions"]})
        inst.to_excel(writer, sheet_name="Instrucciones", index=False)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{tpl["filename"]}"'},
    )


# ============================================================================
# Carga masiva: Notas históricas (estudiante × materia × periodo × docente)
# ============================================================================

NOTAS_REQUIRED = ["Cedula", "Periodo", "CodigoMateria", "Nota"]


async def _ensure_materia(codigo: str, nombre: str) -> str:
    """Busca o crea una materia por código. Devuelve el id."""
    codigo = (codigo or "").strip()
    nombre = (nombre or "").strip() or codigo or "SIN NOMBRE"
    if not codigo:
        codigo = nombre.upper().replace(" ", "-")[:20]
    existing = await db.materias.find_one({"codigo": codigo}, {"_id": 0, "id": 1})
    if existing:
        return existing["id"]
    new_id = str(uuid.uuid4())
    await db.materias.insert_one({
        "id": new_id, "codigo": codigo, "nombre": nombre,
        "facultad_id": None, "programa_id": None,
        "created_at": datetime.utcnow().isoformat(),
    })
    return new_id


async def _ensure_docente(email: str, full_name: str) -> str:
    """Busca o crea un usuario docente por email. Devuelve el user id."""
    email = (email or "").strip().lower()
    if not email:
        return ""
    existing = await db.users.find_one({"email": email}, {"_id": 0, "id": 1})
    if existing:
        return existing["id"]
    new_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": new_id,
        "email": email,
        "password": hash_password("IUDigital2026!"),
        "full_name": (full_name or email.split("@")[0]).strip(),
        "role": "docente",
        "facultad_id": None,
        "programa_id": None,
        "active": True,
        "must_change_password": True,
        "created_at": datetime.utcnow().isoformat(),
        "auto_created": True,
    })
    return new_id


@router.post("/notas")
async def ingest_notas(
    file: UploadFile = File(...),
    user=Depends(require_roles("superadmin", "admin")),
):
    """Ingesta masiva de notas históricas. Crea docentes/materias faltantes."""
    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"No se pudo leer el Excel: {e}")
    df = df.fillna("")
    missing = [c for c in NOTAS_REQUIRED if c not in df.columns]
    if missing:
        raise HTTPException(400, f"Faltan columnas obligatorias: {missing}")

    upload_id = str(uuid.uuid4())
    inserted = 0
    errores = []
    new_docentes = 0
    new_materias = 0
    docs = []
    for idx, row in df.iterrows():
        cedula = str(row.get("Cedula") or "").strip()
        if not cedula:
            errores.append(f"Fila {idx+2}: cédula vacía")
            continue
        try:
            nota = float(row.get("Nota") or 0)
        except Exception:
            errores.append(f"Fila {idx+2}: nota inválida")
            continue
        periodo = str(row.get("Periodo") or "").strip()
        codigo_mat = str(row.get("CodigoMateria") or "").strip()
        nombre_mat = str(row.get("NombreMateria") or "").strip()
        email_doc = str(row.get("EmailDocente") or "").strip().lower()
        nombre_doc = str(row.get("NombreDocente") or "").strip()

        # Track docente/materia existence pre-ensure
        was_new_mat = not await db.materias.find_one({"codigo": codigo_mat or "__none__"}, {"_id": 1}) if codigo_mat else False
        was_new_doc = (not await db.users.find_one({"email": email_doc}, {"_id": 1})) if email_doc else False
        materia_id = await _ensure_materia(codigo_mat, nombre_mat) if codigo_mat or nombre_mat else None
        docente_id = await _ensure_docente(email_doc, nombre_doc) if email_doc else None
        if was_new_mat and materia_id:
            new_materias += 1
        if was_new_doc and docente_id:
            new_docentes += 1

        aprobada = str(row.get("Aprobada") or "").strip().lower()
        aprobada_bool = (aprobada in ("sí", "si", "true", "1", "yes")) if aprobada else (nota >= 3.0)

        docs.append({
            "id": str(uuid.uuid4()),
            "cedula": cedula,
            "periodo": periodo,
            "materia_id": materia_id,
            "materia_codigo": codigo_mat,
            "materia_nombre": nombre_mat,
            "docente_id": docente_id,
            "docente_email": email_doc,
            "docente_nombre": nombre_doc,
            "nota": round(nota, 2),
            "aprobada": aprobada_bool,
            "upload_id": upload_id,
            "created_at": datetime.utcnow().isoformat(),
        })
        inserted += 1

    if docs:
        BATCH = 2000
        for i in range(0, len(docs), BATCH):
            await db.historico_notas.insert_many(docs[i:i + BATCH])

    await db.uploads.insert_one({
        "id": upload_id,
        "tipo": "notas",
        "filename": file.filename,
        "periodo": None,
        "total_rows": int(len(df)),
        "inserted": inserted,
        "errores": len(errores),
        "errores_detalle": errores[:30],
        "docentes_creados": new_docentes,
        "materias_creadas": new_materias,
        "uploaded_by": user["email"],
        "created_at": datetime.utcnow().isoformat(),
    })
    return {
        "ok": True, "id": upload_id, "inserted": inserted,
        "errores": len(errores), "docentes_creados": new_docentes,
        "materias_creadas": new_materias,
    }


# ============================================================================
# Carga masiva: Relación Docente-Materia (con creación automática de docentes)
# ============================================================================

DM_REQUIRED = ["EmailDocente", "CodigoMateria", "Periodo"]


@router.post("/docente-materia-bulk")
async def ingest_docente_materia(
    file: UploadFile = File(...),
    user=Depends(require_roles("superadmin", "admin")),
):
    """Ingesta masiva de relaciones docente-materia. Crea usuarios docentes faltantes."""
    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"No se pudo leer el Excel: {e}")
    df = df.fillna("")
    missing = [c for c in DM_REQUIRED if c not in df.columns]
    if missing:
        raise HTTPException(400, f"Faltan columnas obligatorias: {missing}")

    upload_id = str(uuid.uuid4())
    inserted = 0
    duplicados = 0
    errores = []
    new_docentes = 0
    new_materias = 0

    for idx, row in df.iterrows():
        email_doc = str(row.get("EmailDocente") or "").strip().lower()
        nombre_doc = str(row.get("NombreDocente") or "").strip()
        codigo_mat = str(row.get("CodigoMateria") or "").strip()
        nombre_mat = str(row.get("NombreMateria") or "").strip()
        periodo = str(row.get("Periodo") or "").strip()

        if not email_doc or not codigo_mat or not periodo:
            errores.append(f"Fila {idx+2}: faltan EmailDocente/CodigoMateria/Periodo")
            continue

        was_new_doc = not await db.users.find_one({"email": email_doc}, {"_id": 1})
        was_new_mat = not await db.materias.find_one({"codigo": codigo_mat}, {"_id": 1})
        docente_id = await _ensure_docente(email_doc, nombre_doc)
        materia_id = await _ensure_materia(codigo_mat, nombre_mat)
        if was_new_doc:
            new_docentes += 1
        if was_new_mat:
            new_materias += 1

        # Skip duplicates
        existing = await db.docente_materia.find_one({
            "docente_id": docente_id, "materia_id": materia_id, "periodo": periodo,
        }, {"_id": 1})
        if existing:
            duplicados += 1
            continue

        await db.docente_materia.insert_one({
            "id": str(uuid.uuid4()),
            "docente_id": docente_id,
            "materia_id": materia_id,
            "periodo": periodo,
            "upload_id": upload_id,
            "created_at": datetime.utcnow().isoformat(),
        })
        inserted += 1

    await db.uploads.insert_one({
        "id": upload_id,
        "tipo": "docente_materia",
        "filename": file.filename,
        "periodo": None,
        "total_rows": int(len(df)),
        "inserted": inserted,
        "duplicados": duplicados,
        "errores": len(errores),
        "errores_detalle": errores[:30],
        "docentes_creados": new_docentes,
        "materias_creadas": new_materias,
        "uploaded_by": user["email"],
        "created_at": datetime.utcnow().isoformat(),
    })
    return {
        "ok": True, "id": upload_id, "inserted": inserted,
        "duplicados": duplicados, "errores": len(errores),
        "docentes_creados": new_docentes, "materias_creadas": new_materias,
    }
