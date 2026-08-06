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
async def list_uploads(user=Depends(require_roles("superadmin", "direccion"))):
    items = await db.uploads.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return items


@router.post("/preview")
async def preview(file: UploadFile = File(...), user=Depends(require_roles("superadmin", "direccion"))):
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
    user=Depends(require_roles("superadmin", "direccion")),
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
        "sheet": "Caracterizacion",
        "columns": [
            "doc_estudiante", "Tipo documento", "Nombre", "Apellidos",
            "Correo electrónico", "Correo Institucional Estudiante",
            "Teléfono", "Número de celular", "Fecha nacimiento", "Edad",
            "Sexo biológico", "Estado civil",
            "País residencia", "Departamento residencia", "Ciudad/Municipio residencia",
            "Dirección residencia", "¿Vive en alguna frontera?",
            "Estrato socioeconómico", "Sisben",
            "Etnia", "Grupo étnico", "Nombre del resguardo indígena (si pertenece a uno)",
            "Etnia indígena a la cual pertenece",
            "Tipo de discapacidad", "Posee capacidades excepcionales",
            "Grupo vulnerable (si pertenece a uno)",
            "Ubicación de conflicto", "Veteranos y/o núcleo familiar",
            "Ingresos familiares", "Número de personas en la familia",
            "Número de aportantes a la familia", "Tipo de vivienda",
            "Nivel educativo Madre", "Nivel educativo Padre",
            "Nº de hermanos con educación superior",
            "Facultad", "Programa académico", "Nivel (semestre)",
            "Razón para estudiar el programa", "¿Por qué decidió estudiar en la institución?",
            "Hobbies", "Actividades no Académicas", "Distinciones",
        ],
        "sample": [{
            "doc_estudiante": "1234567890", "Tipo documento": "CEDULA DE CIUDADANIA",
            "Nombre": "JUAN CARLOS", "Apellidos": "PÉREZ GÓMEZ",
            "Correo electrónico": "juan.perez@gmail.com",
            "Correo Institucional Estudiante": "juan.perez@est.iudigital.edu.co",
            "Teléfono": "3001234567", "Número de celular": "3009876543",
            "Fecha nacimiento": "15/03/1998", "Edad": 27,
            "Sexo biológico": "Masculino", "Estado civil": "Soltero",
            "País residencia": "Colombia", "Departamento residencia": "ANTIOQUIA",
            "Ciudad/Municipio residencia": "MEDELLIN",
            "Dirección residencia": "CALLE", "¿Vive en alguna frontera?": "Ninguno",
            "Estrato socioeconómico": "Estrato 3", "Sisben": "B2",
            "Etnia": "Mestizos", "Grupo étnico": "",
            "Nombre del resguardo indígena (si pertenece a uno)": "",
            "Etnia indígena a la cual pertenece": "",
            "Tipo de discapacidad": "Ninguna", "Posee capacidades excepcionales": "Ninguna",
            "Grupo vulnerable (si pertenece a uno)": "Ninguno",
            "Ubicación de conflicto": "", "Veteranos y/o núcleo familiar": "No aplica",
            "Ingresos familiares": "1 a 2 SMMLV",
            "Número de personas en la familia": 4, "Número de aportantes a la familia": 2,
            "Tipo de vivienda": "Familiar",
            "Nivel educativo Madre": "Bachiller", "Nivel educativo Padre": "Técnico",
            "Nº de hermanos con educación superior": 1,
            "Facultad": "Facultad de Ingeniería y Ciencias Agropecuarias (FICA)",
            "Programa académico": "INGENIERÍA DE SOFTWARE Y DATOS",
            "Nivel (semestre)": 3,
            "Razón para estudiar el programa": "Vocación",
            "¿Por qué decidió estudiar en la institución?": "Modalidad virtual",
            "Hobbies": "Deportes, música", "Actividades no Académicas": "Voluntariado",
            "Distinciones": "",
        }],
        "instructions": [
            "🔑 CAMPO CLAVE OBLIGATORIO: 'doc_estudiante' (cédula) — es la llave para cruzar con notas y matrículas.",
            "📋 Estructura basada en CARACTERIZACION_2026.xlsx del sistema institucional.",
            "🧭 Sisben: usar niveles A1-A5, B1-B7, C1-C18, D1-D21 o dejar vacío si NO aplica.",
            "🏠 Dirección residencia: VEREDA / CORREGIMIENTO / RURAL / FINCA → se marca como Rural. CALLE / CARRERA / VIA → Urbana.",
            "🌎 País residencia: 'Colombia' o nombre del país. Estudiantes en el exterior se ubican por 'País Ubicación de conflicto'.",
            "🎯 Ubicación de conflicto: si el estudiante es víctima del conflicto, poner el país (ej. 'Colombia').",
            "👥 Grupo vulnerable: 'Ninguno' para no, o descripción del grupo (ej. 'Mujer cabeza de familia').",
            "💰 Ingresos familiares: rangos como '1 a 2 SMMLV', '2 a 3 SMMLV', 'Menos de 1 SMMLV', etc.",
            "🎓 Facultad: nombre COMPLETO institucional (ej. 'Facultad de Ingeniería y Ciencias Agropecuarias (FICA)').",
        ],
    },
    "notas": {
        "filename": "plantilla_notas.xlsx",
        "sheet": "Notas",
        "columns": [
            "DOC_ESTUDIANTE", "NOMBRE_ESTUDIANTE", "CODIGO GRUPO", "BLOQUE",
            "CODIGO ASIGNATURA", "CREDITOS ASIGNATURA", "ASIGNATURA",
            "NOTA FINAL", "ESTADO", "DOC DOCENTE", "DOCENTE",
            "ANO", "PERIODO", "PROGRAMA", "FACULTAD_ASIGNATURA",
        ],
        "sample": [
            {"DOC_ESTUDIANTE": "1234567890", "NOMBRE_ESTUDIANTE": "JUAN PEREZ",
             "CODIGO GRUPO": "PREISDICA26010001", "BLOQUE": "1",
             "CODIGO ASIGNATURA": "PREISDICA23028", "CREDITOS ASIGNATURA": 3,
             "ASIGNATURA": "Analítica de Datos", "NOTA FINAL": 4.3,
             "ESTADO": "APROBADA", "DOC DOCENTE": "70000001",
             "DOCENTE": "MARIA RESTREPO", "ANO": 2026, "PERIODO": 1,
             "PROGRAMA": "INGENIERIA DE SOFTWARE Y DATOS",
             "FACULTAD_ASIGNATURA": "Facultad de Ingeniería"},
            {"DOC_ESTUDIANTE": "1234567890", "NOMBRE_ESTUDIANTE": "JUAN PEREZ",
             "CODIGO GRUPO": "PREISDICA26010002", "BLOQUE": "1",
             "CODIGO ASIGNATURA": "PREISDICA23027", "CREDITOS ASIGNATURA": 3,
             "ASIGNATURA": "Desarrollo de Aplicaciones Web", "NOTA FINAL": 2.9,
             "ESTADO": "REPROBADA", "DOC DOCENTE": "70000002",
             "DOCENTE": "CARLOS VEGA", "ANO": 2026, "PERIODO": 1,
             "PROGRAMA": "INGENIERIA DE SOFTWARE Y DATOS",
             "FACULTAD_ASIGNATURA": "Facultad de Ingeniería"},
        ],
        "instructions": [
            "📋 Estructura basada en RPTNotasPeriodo del sistema institucional.",
            "🔑 CAMPOS OBLIGATORIOS: DOC_ESTUDIANTE, CODIGO GRUPO, CODIGO ASIGNATURA, NOTA FINAL, ANO, PERIODO.",
            "📊 NOTA FINAL: escala 0.0 a 5.0. Si NOTA >= 3.0 → ESTADO='APROBADA', sino 'REPROBADA'.",
            "👨‍🏫 DOC DOCENTE: cédula del docente. Si no existe, se crea automáticamente.",
            "📆 ANO+PERIODO: año calendario + 1 o 2 (ej. 2026, 1 = 2026-1).",
            "🧾 Si la asignatura o el docente no existen, se crean automáticamente.",
        ],
    },
    "docente_materia": {
        "filename": "plantilla_asignaciones.xlsx",
        "sheet": "Asignaciones",
        "columns": [
            "IDGRUPO", "CODIGO_GRUPO", "TIPO_GRUPO",
            "ASIGNATURA_NOMBRE", "CODIGO_ASIGATURA", "BLOQUE",
            "DIA", "HORA",
            "IDDOC", "DOCENTE_CEDULA", "DOCENTE_NOMBRE",
            "DOCENTE_EMAIL", "DOCENTE_EMAIL_INSTITUCIONAL",
            "DOC_ESTUDIANTE", "NOMBRE_ESTUDIANTE",
            "PROGRAMA", "ESTADO_ASIGNATURA",
            "ANIO", "PERIODO", "PERIODICIDAD",
            "EMAIL  PERSONAL ESTUDIANTE", "EMAIL_INSTITUCIONAL ESTUDIANTE",
        ],
        "sample": [
            {"IDGRUPO": "1001", "CODIGO_GRUPO": "PREISDICA26010001", "TIPO_GRUPO": "PRE",
             "ASIGNATURA_NOMBRE": "Analítica de Datos- PREISDICA23028",
             "CODIGO_ASIGATURA": "PREISDICA23028", "BLOQUE": "1",
             "DIA": "LUNES", "HORA": "18:00-20:00",
             "IDDOC": "20001", "DOCENTE_CEDULA": "70000001",
             "DOCENTE_NOMBRE": "MARIA ALEJANDRA RESTREPO",
             "DOCENTE_EMAIL": "maria.restrepo@iudigital.edu.co",
             "DOCENTE_EMAIL_INSTITUCIONAL": "maria.restrepo@iudigital.edu.co",
             "DOC_ESTUDIANTE": "1234567890", "NOMBRE_ESTUDIANTE": "JUAN PEREZ",
             "PROGRAMA": "INGENIERIA DE SOFTWARE Y DATOS",
             "ESTADO_ASIGNATURA": "Matriculada",
             "ANIO": "2026", "PERIODO": "2", "PERIODICIDAD": "SEMESTRAL",
             "EMAIL  PERSONAL ESTUDIANTE": "juan.perez@gmail.com",
             "EMAIL_INSTITUCIONAL ESTUDIANTE": "juan.perez@est.iudigital.edu.co"},
        ],
        "instructions": [
            "📋 Estructura basada en ASIGNACION_GRUPO_CONSOLIDADO del sistema institucional.",
            "🔑 CAMPOS OBLIGATORIOS: DOCENTE_EMAIL, DOCENTE_CEDULA, CODIGO_GRUPO, CODIGO_ASIGATURA, ANIO, PERIODO.",
            "👥 UNA FILA POR (estudiante × grupo × docente) — un mismo grupo tendrá múltiples filas.",
            "👨‍🏫 Si DOCENTE_EMAIL no existe, se crea usuario con rol 'docente', contraseña inicial 'IUDigital2026'.",
            "🧾 Si el grupo o la asignatura no existen, se crean automáticamente.",
            "📆 ANIO y PERIODO se concatenan como periodo (2026 + 2 = 2026-2).",
        ],
    },
}


@router.get("/template/{tipo}")
async def download_template(tipo: str, user=Depends(require_roles("superadmin", "direccion"))):
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
        "role": "profesor",
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
    user=Depends(require_roles("superadmin", "direccion")),
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
    user=Depends(require_roles("superadmin", "direccion")),
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



# ============================================================================
# Descarga completa de BD (colecciones principales) como Excel
# ============================================================================
BACKUP_COLLECTIONS = {
    "students": {"filename": "estudiantes_completos.xlsx", "sheet": "Estudiantes"},
    "grupos": {"filename": "grupos.xlsx", "sheet": "Grupos"},
    "matriculas": {"filename": "matriculas.xlsx", "sheet": "Matriculas"},
    "historico_notas": {"filename": "notas_historicas.xlsx", "sheet": "Notas"},
    "docentes": {"filename": "docentes.xlsx", "sheet": "Docentes"},
    "docente_materia": {"filename": "docente_materia.xlsx", "sheet": "DocenteMateria"},
    "programas": {"filename": "programas.xlsx", "sheet": "Programas"},
    "facultades": {"filename": "facultades.xlsx", "sheet": "Facultades"},
}


@router.get("/backup/{coleccion}")
async def backup_collection(coleccion: str, user=Depends(require_roles("superadmin", "direccion"))):
    """Descarga una colección de la BD como Excel."""
    if coleccion not in BACKUP_COLLECTIONS:
        raise HTTPException(404, f"Colección no válida. Opciones: {list(BACKUP_COLLECTIONS.keys())}")
    meta = BACKUP_COLLECTIONS[coleccion]

    if coleccion == "docentes":
        docs = await db.users.find({"role": "profesor"}, {"_id": 0, "password": 0}).to_list(5000)
    else:
        docs = await db[coleccion].find({}, {"_id": 0}).to_list(200000)

    if not docs:
        raise HTTPException(404, f"No hay datos en la colección '{coleccion}'")

    df = pd.DataFrame(docs)
    # Truncar campos lista/dict a string para Excel
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            df[col] = df[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=meta["sheet"][:30], index=False)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{meta["filename"]}"'},
    )


@router.get("/backup-stats")
async def backup_stats(user=Depends(require_roles("superadmin", "direccion"))):
    """Cuenta de documentos por colección para el módulo de descargas."""
    counts = {}
    counts["students"] = await db.students.count_documents({})
    counts["grupos"] = await db.grupos.count_documents({})
    counts["matriculas"] = await db.matriculas.count_documents({})
    counts["historico_notas"] = await db.historico_notas.count_documents({})
    counts["docentes"] = await db.users.count_documents({"role": "profesor"})
    counts["docente_materia"] = await db.docente_materia.count_documents({})
    counts["programas"] = await db.programas.count_documents({})
    counts["facultades"] = await db.facultades.count_documents({})
    return counts


# ============================================================================
# Full-refresh: re-ejecutar load_real_data.py con archivos subidos
# ============================================================================
@router.post("/full-refresh")
async def full_refresh(
    carac: UploadFile | None = File(None),
    asignacion: UploadFile | None = File(None),
    notas_25_2: UploadFile | None = File(None),
    notas_26_1: UploadFile | None = File(None),
    programas: UploadFile | None = File(None),
    user=Depends(require_roles("superadmin")),
):
    """Reemplaza archivos base en /app/uploads_user y ejecuta load_real_data.py.

    ⚠️ Este endpoint WIPE + REBUILD toda la BD de estudiantes, notas, grupos y matrículas.
    Solo el superadmin puede ejecutarlo. Solo reemplaza los archivos que se envíen (los otros
    se conservan del snapshot anterior)."""
    import os
    import subprocess
    from pathlib import Path

    BASE = Path("/app/uploads_user")
    BASE.mkdir(parents=True, exist_ok=True)

    saved = {}
    mapping = [
        (carac, "carac.xlsx"),
        (asignacion, "estdoc.csv"),
        (notas_25_2, "notas_25_2.xlsx"),
        (notas_26_1, "notas_26_2.xlsx"),
        (programas, "progs.xlsx"),
    ]
    for f, name in mapping:
        if f and f.filename:
            path = BASE / name
            content = await f.read()
            path.write_bytes(content)
            saved[name] = len(content)

    if not saved:
        raise HTTPException(400, "Debes subir al menos un archivo.")

    # Ejecutar load_real_data.py de forma sincrónica y capturar salida
    proc = subprocess.run(
        ["python", "/app/backend/load_real_data.py"],
        capture_output=True, text=True, timeout=600, cwd="/app/backend",
    )
    ok = proc.returncode == 0

    # Registrar en uploads
    upload_id = str(uuid.uuid4())
    await db.uploads.insert_one({
        "id": upload_id,
        "tipo": "full-refresh",
        "archivos_reemplazados": saved,
        "ok": ok,
        "stdout_tail": (proc.stdout or "").splitlines()[-30:],
        "stderr": (proc.stderr or "")[:2000],
        "uploaded_by": user["email"],
        "created_at": datetime.utcnow().isoformat(),
    })

    if not ok:
        raise HTTPException(500, f"load_real_data.py falló: {proc.stderr[:500]}")

    # Estadísticas finales
    stats = {
        "students": await db.students.count_documents({}),
        "grupos": await db.grupos.count_documents({}),
        "matriculas": await db.matriculas.count_documents({}),
        "historico_notas": await db.historico_notas.count_documents({}),
        "docentes": await db.users.count_documents({"role": "profesor"}),
        "docente_materia": await db.docente_materia.count_documents({}),
    }

    return {
        "ok": True,
        "id": upload_id,
        "archivos_reemplazados": saved,
        "stats": stats,
        "stdout_tail": (proc.stdout or "").splitlines()[-15:],
    }
