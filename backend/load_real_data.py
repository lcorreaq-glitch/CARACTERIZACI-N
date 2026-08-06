"""One-shot loader: wipe demo data and ingest the 5 REAL institutional Excel files.
Files expected in /app/uploads_user/:
  - carac.xlsx (CARACTERIZACION_2026.xlsx)
  - estdoc.csv (ESTUDIANTES_DOCENTE_ASIGNADO_2026_2.csv, sep=';')
  - notas_25_2.xlsx (NOTAS_ESTUDIANTES_2025_2.xlsx)
  - notas_26_2.xlsx (NOTAS_ESTUDIANTES_2026_2.xlsx)
  - progs.xlsx (PROGRAMAS_IUD_2026_2.xlsx)

Homologa nombres nuevos → esquema existente en Mongo.
Clave de cruce: cedula (doc_estudiante).
"""
import asyncio
import os
import re
import uuid
from datetime import datetime, date
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import pandas as pd
import bcrypt

load_dotenv("/app/backend/.env")
BASE = "/app/uploads_user"


def hash_pwd(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def _norm(s):
    if pd.isna(s) or s is None:
        return ""
    return str(s).strip()


def _upper(s):
    return _norm(s).upper()


def _int(v, default=0):
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except Exception:
        return default


def _float(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def _bool_from_text(v):
    s = _norm(v).lower()
    if not s:
        return False
    return s not in ("no", "no aplica", "ninguna", "ninguno", "false", "0", "n", "sin dato")


# ---- Parsers específicos ----
def parse_edad(fecha_nac, edad_directa=None):
    e = _int(edad_directa)
    if e > 0:
        return e
    try:
        if pd.isna(fecha_nac):
            return 0
        s = _norm(fecha_nac)
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                d = datetime.strptime(s, fmt).date()
                today = date(2026, 8, 1)
                return today.year - d.year - ((today.month, today.day) < (d.month, d.day))
            except Exception:
                continue
    except Exception:
        pass
    return 0


def rango_edad(e):
    if not e or e < 18: return "Menor 18"
    if e <= 22: return "18-22"
    if e <= 27: return "23-27"
    if e <= 32: return "28-32"
    if e <= 40: return "33-40"
    if e <= 50: return "41-50"
    return "51+"


def parse_estrato(s):
    s = _upper(s)
    if not s or "SIN" in s: return "SIN DATO"
    m = re.search(r"\d", s)
    return f"ESTRATO {m.group(0)}" if m else "SIN DATO"


def parse_sisben(s):
    s = _upper(s)
    if not s or s in ("NO APLICA", "N/A", "SIN DATO", "NINGUNA"):
        return "NO APLICA", False, "NO APLICA"
    # levels like A1..D21
    if re.fullmatch(r"[A-D]\d{1,2}", s):
        grupo = f"GRUPO {s[0]}"
        return s, True, grupo
    if s.startswith("GRUPO"):
        return s, True, s
    return s, True, "NO APLICA"


def parse_ingresos(s):
    if pd.isna(s): return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    txt = _norm(s).lower().replace(",", "").replace(".", "")
    # ranges like "1 a 2 SMMLV" → approximate mid
    if "menos" in txt or "< 1" in txt:
        return 700000
    if "1 a 2" in txt or "1 - 2" in txt:
        return 1800000
    if "2 a 3" in txt: return 3000000
    if "3 a 5" in txt: return 4500000
    if "5" in txt and ("mas" in txt or "más" in txt or "+" in txt): return 7000000
    nums = re.findall(r"\d+", txt)
    if nums:
        n = int(nums[0])
        return float(n) if n > 100000 else float(n * 1000000)
    return 0.0


def rango_ingresos(v):
    if not v: return "Sin dato"
    if v < 1300000: return "< 1 SMMLV"
    if v < 2600000: return "1 a 2 SMMLV"
    if v < 3900000: return "2 a 3 SMMLV"
    if v < 6500000: return "3 a 5 SMMLV"
    return "5+ SMMLV"


def parse_genero(s):
    s = _upper(s)
    if not s: return "NO INFORMA"
    if s.startswith("FEM"): return "FEMENINO"
    if s.startswith("MASC"): return "MASCULINO"
    if "OTRO" in s: return "OTRO"
    return "NO INFORMA"


def parse_ubicacion(pais_res, ciudad, dep):
    """Clasifica Urbana/Rural. Como el archivo no trae columna directa,
    usamos una lista de las ~130 ciudades principales de Colombia."""
    URBANAS = {
        'MEDELLIN','MEDELLÍN','BOGOTA','BOGOTÁ','BOGOTA D.C.','CALI','SANTIAGO DE CALI','BARRANQUILLA',
        'CARTAGENA','CARTAGENA DE INDIAS','BUCARAMANGA','PEREIRA','MANIZALES','IBAGUE','IBAGUÉ',
        'CUCUTA','CÚCUTA','SAN JOSÉ DE CÚCUTA','MONTERIA','MONTERÍA','SANTA MARTA','VILLAVICENCIO',
        'NEIVA','ARMENIA','PASTO','POPAYAN','POPAYÁN','VALLEDUPAR','SINCELEJO','TUNJA','QUIBDO','QUIBDÓ',
        'FLORENCIA','RIOHACHA','YOPAL','MOCOA','LETICIA','ARAUCA','INIRIDA','INÍRIDA','MITU','MITÚ',
        'PUERTO CARREÑO','SAN ANDRES','SAN ANDRÉS','ITAGUI','ITAGÜÍ','ENVIGADO','BELLO','SOACHA','SOLEDAD',
        'MALAMBO','APARTADO','APARTADÓ','TURBO','RIONEGRO','SABANETA','LA ESTRELLA','COPACABANA',
        'GIRARDOTA','CALDAS','CAUCASIA','GUARNE','PALMIRA','BUENAVENTURA','TULUÁ','TULUA','CARTAGO',
        'JAMUNDÍ','JAMUNDI','YUMBO','FLORIDABLANCA','GIRÓN','GIRON','PIEDECUESTA','DOSQUEBRADAS',
        'SANTA ROSA DE CABAL','LA DORADA','CHINCHINÁ','CHIA','CHÍA','ZIPAQUIRÁ','ZIPAQUIRA',
        'FACATATIVÁ','FACATATIVA','MOSQUERA','MADRID','CAJICÁ','CAJICA','FUSAGASUGÁ','FUSAGASUGA','FUNZA',
        'DUITAMA','SOGAMOSO','MONTELÍBANO','MONTELIBANO','CERETÉ','CERETE','LORICA','MAGANGUÉ','MAGANGUE',
        'TURBACO','BARRANCABERMEJA','MALAGA','MÁLAGA','SOCORRO','SAN GIL','AGUACHICA','MAICAO','FONSECA',
        'SAN ANDRÉS DE TUMACO','TUMACO','IPIALES','OCAÑA','PAMPLONA','LOS PATIOS','VILLA DEL ROSARIO',
        'BOSCONIA','CIÉNAGA','CIENAGA','ESPINAL','FLANDES','MARIQUITA','HONDA','GIRARDOT','MELGAR',
        'LA MESA','LA CEJA',
    }
    p = _upper(pais_res)
    ciudad_u = _upper(ciudad)
    if not ciudad_u or ciudad_u == "SIN DATO":
        return "Sin dato"
    if p and p != "COLOMBIA":
        return "Urbana"  # residentes en el exterior se asumen urbanos
    RURAL_KEYS = ("VEREDA", "CORREGIMIENTO", "RURAL")
    if any(k in ciudad_u for k in RURAL_KEYS):
        return "Rural"
    return "Urbana" if ciudad_u in URBANAS else "Rural"


# =============================================================================
async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    print("=== 1) Wipe demo data ===")
    for coll in ["students", "historico_notas", "docente_materia", "materias", "grupos", "matriculas", "uploads"]:
        r = await db[coll].delete_many({})
        print(f"  {coll}: eliminados {r.deleted_count}")
    # Delete auto-created docentes (keep superadmin + docente.demo)
    r = await db.users.delete_many({
        "role": "docente",
        "email": {"$nin": ["docente.demo@iudigital.edu.co"]}
    })
    print(f"  users(docentes): eliminados {r.deleted_count}")

    # =========================================================================
    print("\n=== 2) Cargar PROGRAMAS (catálogo) ===")
    progs = pd.read_excel(f"{BASE}/progs.xlsx", sheet_name=0)
    prog_docs = []
    fac_map = {}  # nombre_facultad -> id
    for _, row in progs.iterrows():
        fac_name = _norm(row.get("FACULTAD"))
        if not fac_name:
            continue
        if fac_name not in fac_map:
            fac_map[fac_name] = str(uuid.uuid4())
        prog_docs.append({
            "id": str(uuid.uuid4()),
            "nombre": _norm(row.get("NOMBRE_DEL_PROGRAMA")),
            "nombre_corto": _norm(row.get("NOMBRE_CORTO")),
            "codigo": _norm(row.get("CÓDIGO_SNIES_DEL_PROGRAMA")),
            "facultad_id": fac_map[fac_name],
            "facultad_nombre": fac_name,
            "facultad_corta": _norm(row.get("NOMBRE_CORTO_FAC")),
            "nivel": _norm(row.get("NIVEL_ACADÉMICO")),
            "modalidad": _norm(row.get("MODALIDAD")),
            "estado": _norm(row.get("ESTADO_PROGRAMA")),
            "created_at": datetime.utcnow().isoformat(),
        })
    # Save facultades
    await db.facultades.delete_many({})
    fac_docs = [{"id": fid, "nombre": fn, "created_at": datetime.utcnow().isoformat()}
                for fn, fid in fac_map.items()]
    if fac_docs:
        await db.facultades.insert_many(fac_docs)
    await db.programas.delete_many({})
    if prog_docs:
        await db.programas.insert_many(prog_docs)
    print(f"  Facultades: {len(fac_docs)} · Programas: {len(prog_docs)}")

    # Index programas por nombre (upper)
    prog_by_name = {p["nombre"].upper(): p for p in prog_docs}

    # =========================================================================
    print("\n=== 3) Cargar ASIGNACIÓN (grupos + docentes + matrículas) ===")
    df = pd.read_csv(f"{BASE}/estdoc.csv", sep=";", dtype=str, on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]

    docente_by_cedula = {}  # cedula -> user_id
    docente_by_email = {}   # email -> user_id
    docente_meta = {}       # uid -> {correo_personal, correo_institucional, iddoc}
    # Pre-populate with existing users to avoid dupes (superadmin, demo)
    async for u in db.users.find({}, {"_id": 0, "id": 1, "email": 1}):
        if u.get("email"):
            docente_by_email[u["email"].lower()] = u["id"]

    grupos_map = {}         # codigo_grupo -> grupo doc
    matriculas = []
    docente_users = []

    def _extract_asig_codigo(cod_direct, asig_nombre):
        """Extrae código de asignatura del nombre si viene vacío en el campo directo.
        Patrón típico: 'Nombre materia - CODIGOMATERIA24014'."""
        if cod_direct:
            return cod_direct
        if not asig_nombre or "-" not in asig_nombre:
            return ""
        # Última parte tras el último "- "
        tail = asig_nombre.rsplit("-", 1)[-1].strip()
        # Debe ser un código alfanumérico razonable (>=6 chars, sin espacios)
        if 6 <= len(tail) <= 30 and " " not in tail and tail.upper() == tail.upper():
            return tail
        return ""

    for _, row in df.iterrows():
        # Docente
        doc_ced = _norm(row.get("DOCENTE_CEDULA"))
        email_personal = _norm(row.get("DOCENTE_EMAIL")).lower()
        email_inst = _norm(row.get("DOCENTE_EMAIL_INSTITUCIONAL")).lower()
        doc_email = email_inst or email_personal  # priorizar institucional para login
        doc_name = " ".join(_norm(row.get("DOCENTE_NOMBRE")).split())  # limpia dobles espacios
        iddoc = _norm(row.get("IDDOC"))
        if doc_ced and doc_ced not in docente_by_cedula:
            # Deduplicate by email
            existing_uid = docente_by_email.get(doc_email) if doc_email else None
            if existing_uid:
                docente_by_cedula[doc_ced] = existing_uid
                docente_meta[existing_uid] = {
                    "correo_personal": email_personal,
                    "correo_institucional": email_inst,
                    "iddoc": iddoc,
                    "cedula": doc_ced,
                }
            else:
                uid = str(uuid.uuid4())
                docente_by_cedula[doc_ced] = uid
                if doc_email:
                    docente_by_email[doc_email] = uid
                docente_users.append({
                    "id": uid,
                    "email": doc_email or f"docente_{doc_ced}@iudigital.edu.co",
                    "password": hash_pwd("IUDigital2026"),
                    "full_name": doc_name or f"Docente {doc_ced}",
                    "role": "docente",
                    "documento": doc_ced,
                    "cedula": doc_ced,
                    "iddoc": iddoc,
                    "correo_personal": email_personal,
                    "correo_institucional": email_inst,
                    "active": True,
                    "must_change_password": True,
                    "created_at": datetime.utcnow().isoformat(),
                })

        # Grupo (upsert: enriquecer si ya existe con datos faltantes)
        codigo_grupo = _norm(row.get("CODIGO_GRUPO"))
        if codigo_grupo:
            programa = _norm(row.get("PROGRAMA")).upper()
            asig_nombre = _norm(row.get("ASIGNATURA_NOMBRE"))
            asig_codigo = _extract_asig_codigo(_norm(row.get("CODIGO_ASIGATURA")), asig_nombre)
            prog_info = prog_by_name.get(programa, {})
            if codigo_grupo not in grupos_map:
                grupos_map[codigo_grupo] = {
                    "id": str(uuid.uuid4()),
                    "codigo_grupo": codigo_grupo,
                    "id_grupo": _norm(row.get("IDGRUPO")),
                    "asignatura_nombre": asig_nombre,
                    "asignatura_codigo": asig_codigo,
                    "bloque": _norm(row.get("BLOQUE")),
                    "dia": _norm(row.get("DIA")),
                    "hora": _norm(row.get("HORA")),
                    "docente_id": docente_by_cedula.get(doc_ced),
                    "docente_nombre": doc_name,
                    "docente_email": doc_email,
                    "docente_correo_personal": email_personal,
                    "docente_correo_institucional": email_inst,
                    "docente_cedula": doc_ced,
                    "programa": programa,
                    "facultad": prog_info.get("facultad_nombre", ""),
                    "periodo": f"{_norm(row.get('ANIO'))}-{_norm(row.get('PERIODO')).strip()}",
                    "periodicidad": _norm(row.get("PERIODICIDAD")),
                    "created_at": datetime.utcnow().isoformat(),
                }
            else:
                # Enriquecer grupo existente si le faltaban datos
                g = grupos_map[codigo_grupo]
                if not g.get("programa") and programa:
                    g["programa"] = programa
                    if prog_info.get("facultad_nombre"):
                        g["facultad"] = prog_info["facultad_nombre"]
                if not g.get("asignatura_codigo") and asig_codigo:
                    g["asignatura_codigo"] = asig_codigo
                if not g.get("docente_id") and docente_by_cedula.get(doc_ced):
                    g["docente_id"] = docente_by_cedula.get(doc_ced)
                    g["docente_nombre"] = doc_name
                    g["docente_email"] = doc_email
                    g["docente_correo_personal"] = email_personal
                    g["docente_correo_institucional"] = email_inst
                    g["docente_cedula"] = doc_ced

        # Matrícula
        ced_est = _norm(row.get("DOC_ESTUDIANTE"))
        if ced_est and codigo_grupo:
            matriculas.append({
                "id": str(uuid.uuid4()),
                "cedula": ced_est,
                "codigo_grupo": codigo_grupo,
                "asignatura_codigo": _extract_asig_codigo(_norm(row.get("CODIGO_ASIGATURA")), _norm(row.get("ASIGNATURA_NOMBRE"))),
                "asignatura_nombre": _norm(row.get("ASIGNATURA_NOMBRE")),
                "docente_id": docente_by_cedula.get(doc_ced),
                "docente_cedula": doc_ced,
                "docente_nombre": doc_name,
                "programa": _norm(row.get("PROGRAMA")).upper(),
                "periodo": f"{_norm(row.get('ANIO'))}-{_norm(row.get('PERIODO')).strip()}",
                "estado": _norm(row.get("ESTADO_ASIGNATURA")),
                "email_estudiante": _norm(row.get("EMAIL  PERSONAL ESTUDIANTE")),
                "email_institucional_estudiante": _norm(row.get("EMAIL_INSTITUCIONAL ESTUDIANTE")),
                "created_at": datetime.utcnow().isoformat(),
            })

    if docente_users:
        await db.users.insert_many(docente_users)
    print(f"  Docentes creados: {len(docente_users)}")

    # Actualizar meta en docentes ya existentes (deduplicados por email)
    for uid, meta in docente_meta.items():
        await db.users.update_one(
            {"id": uid},
            {"$set": {k: v for k, v in meta.items() if v}}
        )
    if grupos_map:
        await db.grupos.insert_many(list(grupos_map.values()))
    print(f"  Grupos: {len(grupos_map)}")
    # Batch matriculas
    if matriculas:
        for i in range(0, len(matriculas), 5000):
            await db.matriculas.insert_many(matriculas[i:i+5000])
    print(f"  Matrículas: {len(matriculas)}")

    # Build estado_matricula por estudiante (más reciente)
    est_estado = {}
    for m in matriculas:
        c = m["cedula"]
        if m.get("estado"):
            est_estado[c] = "Estudiante Matriculado" if "matricul" in m["estado"].lower() else m["estado"]

    # =========================================================================
    print("\n=== 4) Cargar CARACTERIZACIÓN (estudiantes) ===")
    df = pd.read_excel(f"{BASE}/carac.xlsx", sheet_name=0)
    df.columns = [c.strip() for c in df.columns]

    # Import DIVIPOLA lookup
    import sys
    sys.path.insert(0, "/app/backend")
    from divipola import lookup as divipola_lookup

    students = []
    seen = set()
    for _, row in df.iterrows():
        ced = _norm(row.get("doc_estudiante"))
        if not ced or ced in seen:
            continue
        seen.add(ced)

        edad = parse_edad(row.get("Fecha nacimiento"), row.get("Edad"))
        sisben_nivel, sisben_tiene, grupo_sisben = parse_sisben(row.get("Sisben"))
        ingresos = parse_ingresos(row.get("Ingresos familiares"))
        programa = _norm(row.get("Programa académico")).upper()
        prog_info = prog_by_name.get(programa, {})
        facultad = _norm(row.get("Facultad")) or prog_info.get("facultad_nombre", "")

        # Geolocalización
        ciudad = _norm(row.get("Ciudad/Municipio residencia"))
        depto = _norm(row.get("Departamento residencia"))
        pais = _norm(row.get("País residencia")) or "COLOMBIA"
        muni = divipola_lookup(name=ciudad) if ciudad else None

        etnia = _upper(row.get("Etnia")) or "NO APLICA"
        grupo_etnia = _norm(row.get("Grupo étnico"))
        discap_tipo = _upper(row.get("Tipo de discapacidad")) or "NINGUNA"
        discap_flag = discap_tipo not in ("NINGUNA", "NINGUNO", "NO APLICA", "SIN DATO", "")
        vulnerable_txt = _norm(row.get("Grupo vulnerable (si pertenece a uno)"))
        vulnerable = bool(vulnerable_txt) and vulnerable_txt.lower() not in ("no", "no aplica", "ninguno", "ninguna", "sin dato", "n/a", "-")
        # Víctima del conflicto: derivar del texto de vulnerabilidad, NO de "Ubicación de conflicto"
        # que solo indica lugar. Criterio: contiene "víctim", "desplaz" o "conflict".
        vt_lower = vulnerable_txt.lower()
        victima = vulnerable and any(k in vt_lower for k in ("victim", "víctim", "desplaz", "conflict"))

        students.append({
            "id": str(uuid.uuid4()),
            "cedula": ced,
            "tipo_documento": _upper(row.get("Tipo documento")) or "CEDULA",
            "nombre": _norm(row.get("Nombre")),
            "apellidos": _norm(row.get("Apellidos")),
            "nombre_completo": _norm(row.get("nombre_estudiante")),
            "correo": _norm(row.get("Correo electrónico")),
            "correo_institucional": _norm(row.get("Correo Institucional Estudiante")),
            "telefono": _norm(row.get("Teléfono")) or _norm(row.get("Número de celular")),
            "fecha_nacimiento": _norm(row.get("Fecha nacimiento")),
            "edad": edad,
            "rango_edad": rango_edad(edad),
            "genero": parse_genero(row.get("Sexo biológico")),
            "estado_civil": _upper(row.get("Estado civil")) or "NO INFORMA",
            "estrato": parse_estrato(row.get("Estrato socioeconómico")),
            "sisben_nivel": sisben_nivel,
            "sisben_tiene": sisben_tiene,
            "grupo_sisben": grupo_sisben,
            "etnia": etnia,
            "etnia_institucional": _norm(row.get("Etnia indígena a la cual pertenece")),
            "grupo_etnia": grupo_etnia,
            "resguardo_indigena": bool(_norm(row.get("Nombre del resguardo indígena (si pertenece a uno)"))),
            "discapacidad_flag": discap_flag,
            "discapacidad_tipo": discap_tipo,
            "capacidad_excepcional": _upper(row.get("Posee capacidades excepcionales")) or "NINGUNA",
            "grupo_vulnerable": vulnerable,
            "tipo_grupo_vulnerable": vulnerable_txt.upper() if vulnerable else "SIN DATO",
            "victima_conflicto": victima,
            "veterano": _upper(row.get("Veteranos y/o núcleo familiar")) or "NO APLICA",
            "tipo_ubicacion": parse_ubicacion(pais, ciudad, depto),
            "zona_frontera": _upper(row.get("¿Vive en alguna frontera?")) or "NO APLICA",
            "ingresos_flia": ingresos,
            "rango_ingresos": rango_ingresos(ingresos),
            "num_personas_flia": _int(row.get("Número de personas en la familia")),
            "num_aportantes": _int(row.get("Número de aportantes a la familia")),
            "hnos_educ_superior": _int(row.get("Nº de hermanos con educación superior")),
            "vivienda_propia": _upper(row.get("Tipo de vivienda")) in ("PROPIA", "PROPIA CON HIPOTECA"),
            "nivel_educ_madre": _upper(row.get("Nivel educativo Madre")) or "NO INFORMA",
            "nivel_educ_padre": _upper(row.get("Nivel educativo Padre")) or "NO INFORMA",
            "parentesco_emergencia": _upper(row.get("Parentesco")),
            "razon_carrera_cat": _norm(row.get("categoria Razón para estudiar el programa")) or _norm(row.get("Razón para estudiar el programa")),
            "razon_institucion": _norm(row.get("categoria ¿Por qué decidió estudiar en la institución?")) or _norm(row.get("¿Por qué decidió estudiar en la institución?")),
            "hobbies": _norm(row.get("Hobbies")),
            "actividades": _norm(row.get("Actividades no Académicas")),
            "hobbies_cat": [_norm(row.get("Hobbies"))] if _norm(row.get("Hobbies")) else [],
            "actividades_cat": [_norm(row.get("Actividades no Académicas"))] if _norm(row.get("Actividades no Académicas")) else [],
            "tiene_distinciones": bool(_norm(row.get("Distinciones"))),
            "programa": programa,
            "facultad": facultad,
            "nivel": _int(row.get("Nivel (semestre)")),
            "estado_matricula": est_estado.get(ced, "Sin matrícula 2026-2"),
            "ciudad_nombre": muni["nombre"] if muni else (ciudad.upper() if ciudad else "SIN DATO"),
            "ciudad_codigo": muni["codigo"] if muni else "",
            "departamento": muni["departamento"] if muni else (depto.upper() if depto else ""),
            "pais": pais.upper(),
            "lat": muni["lat"] if muni else 0,
            "lon": muni["lon"] if muni else 0,
            "periodo": "2026-2",
            "promedio": 0.0,   # se calcula desde notas
            "total_materias": 0.0,
            "aprobadas": 0.0,
            "reprobadas": 0.0,
            "pendientes": 0.0,
            "avance_pct": 0.0,
            "created_at": datetime.utcnow().isoformat(),
        })
    if students:
        for i in range(0, len(students), 2000):
            await db.students.insert_many(students[i:i+2000])
    print(f"  Estudiantes: {len(students)}")

    # =========================================================================
    print("\n=== 5) Cargar NOTAS (2025-2 y 2026-2) ===")
    def norm_note_cols(df):
        df.columns = [c.strip() for c in df.columns]
        return df

    notas_all = []
    for path, per_fallback in [(f"{BASE}/notas_25_2.xlsx", "2025-2"), (f"{BASE}/notas_26_2.xlsx", "2026-1")]:
        d = norm_note_cols(pd.read_excel(path, sheet_name=0))
        for _, r in d.iterrows():
            ced = _norm(r.get("DOC_ESTUDIANTE"))
            if not ced:
                continue
            nota = _float(r.get("NOTA FINAL"))
            estado = _norm(r.get("ESTADO"))
            doc_ced = _norm(r.get("DOC DOCENTE"))
            if doc_ced.endswith(".0"):
                doc_ced = doc_ced[:-2]
            docente_id = docente_by_cedula.get(doc_ced)
            # Periodo real desde columnas ANO/PERIODO (más confiable que el nombre del archivo)
            anio_val = _int(r.get("ANO"), _int(r.get("AÑO")))
            per_val = _int(r.get("PERIODO"))
            periodo_real = f"{anio_val}-{per_val}" if (anio_val and per_val) else per_fallback
            notas_all.append({
                "id": str(uuid.uuid4()),
                "cedula": ced,
                "nombre_estudiante": _norm(r.get("NOMBRE_ESTUDIANTE")),
                "codigo_grupo": _norm(r.get("CODIGO GRUPO")),
                "bloque": _norm(r.get("BLOQUE")),
                "codigo_asignatura": _norm(r.get("CODIGO ASIGNATURA")),
                "asignatura_nombre": _norm(r.get("ASIGNATURA")),
                "creditos": _int(r.get("CREDITOS ASIGNATURA")),
                "nota": nota,
                "aprobada": nota >= 3.0,
                "estado": estado,
                "docente_id": docente_id,
                "docente_cedula": doc_ced,
                "docente_nombre": _norm(r.get("DOCENTE")),
                "anio": anio_val,
                "periodo_num": per_val,
                "periodo": periodo_real,
                "programa": _upper(r.get("PROGRAMA")),
                "area_formacion": _norm(r.get("FACULTAD_ASIGNATURA")),
                "created_at": datetime.utcnow().isoformat(),
            })
    if notas_all:
        for i in range(0, len(notas_all), 5000):
            await db.historico_notas.insert_many(notas_all[i:i+5000])
    print(f"  Notas totales: {len(notas_all)}")

    # =========================================================================
    print("\n=== 6) Calcular promedios/aprobadas por estudiante (último periodo con notas) ===")
    # Detectar automáticamente el último periodo con notas
    periodos_con_notas = await db.historico_notas.distinct("periodo")
    ultimo_periodo = sorted(periodos_con_notas)[-1] if periodos_con_notas else "2026-1"
    print(f"  Último periodo detectado: {ultimo_periodo}")
    pipe = [
        {"$match": {"periodo": ultimo_periodo}},
        {"$group": {
            "_id": "$cedula",
            "prom": {"$avg": "$nota"},
            "total": {"$sum": 1},
            "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}},
            "repro": {"$sum": {"$cond": [{"$and": [{"$lt": ["$nota", 3.0]}, {"$gt": ["$nota", 0]}]}, 1, 0]}},
        }},
    ]
    async for row in db.historico_notas.aggregate(pipe):
        c = row["_id"]
        total = row["total"] or 1
        prom = row["prom"] or 0
        aprob = row["aprob"]
        repro = row["repro"]
        avance = (aprob / total * 100.0) if total else 0
        await db.students.update_one(
            {"cedula": c},
            {"$set": {
                "promedio": round(prom, 2),
                "total_materias": total,
                "aprobadas": aprob,
                "reprobadas": repro,
                "pendientes": total - aprob - repro,
                "avance_pct": round(avance, 2),
            }}
        )

    total_est = await db.students.count_documents({})
    docs_creados = await db.users.count_documents({"role": "docente"})
    grupos_c = await db.grupos.count_documents({})
    matr_c = await db.matriculas.count_documents({})
    notas_c = await db.historico_notas.count_documents({})
    print(f"\n=== ✅ RESUMEN FINAL ===")
    print(f"  Estudiantes:    {total_est:,}")
    print(f"  Docentes:       {docs_creados:,}")
    print(f"  Grupos:         {grupos_c:,}")
    print(f"  Matrículas:     {matr_c:,}")
    print(f"  Notas:          {notas_c:,}")
    print(f"  Facultades:     {await db.facultades.count_documents({})}")
    print(f"  Programas:      {await db.programas.count_documents({})}")


if __name__ == "__main__":
    asyncio.run(main())
