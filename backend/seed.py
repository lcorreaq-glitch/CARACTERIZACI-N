"""Seed initial superadmin user and demo students from Excel (if present)."""
import os
from datetime import datetime
from pathlib import Path
import random
import pandas as pd
from database import db
from auth import hash_password
from divipola import MUNICIPIOS, lookup
import uuid

EXCEL_PATH = Path("/app/data/caracterizacion.xlsx")


async def seed_superadmin():
    existing = await db.users.find_one({"email": "lcorreaq@gmail.com"})
    if existing:
        return
    user = {
        "id": str(uuid.uuid4()),
        "email": "lcorreaq@gmail.com",
        "password": hash_password("Chocolate1"),
        "full_name": "Superadministrador IU Digital",
        "role": "superadmin",
        "active": True,
        "must_change_password": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.users.insert_one(user)
    print("[seed] Superadmin created lcorreaq@gmail.com / Chocolate1")


def _b(v):
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("sí", "si", "true", "1", "yes", "y", "x")


def _calc_edad(fecha_str):
    """Calcula la edad a partir de fecha DD/MM/AAAA. Devuelve int o None."""
    if not fecha_str:
        return None
    try:
        from datetime import datetime as _dt
        s = str(fecha_str).strip()
        # try common formats
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                d = _dt.strptime(s.split(" ")[0], fmt)
                today = _dt.now()
                age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
                if 10 <= age <= 100:
                    return age
            except Exception:
                continue
    except Exception:
        pass
    return None


def _rango_edad(e):
    if e is None:
        return "Sin dato"
    if e < 20:
        return "Menor de 20"
    if e < 25:
        return "20 a 24"
    if e < 30:
        return "25 a 29"
    if e < 35:
        return "30 a 34"
    if e < 45:
        return "35 a 44"
    if e < 55:
        return "45 a 54"
    return "55 o más"


def _rango_ingresos(ing):
    if ing is None or ing <= 0:
        return "Sin dato"
    smmlv = 1423500  # SMMLV Colombia 2025 aproximado
    if ing < smmlv:
        return "< 1 SMMLV"
    if ing < smmlv * 2:
        return "1 a 2 SMMLV"
    if ing < smmlv * 3:
        return "2 a 3 SMMLV"
    if ing < smmlv * 5:
        return "3 a 5 SMMLV"
    return "5+ SMMLV"


def _cat_razon_carrera(txt):
    """Categoriza C_strRazonCarrera (texto libre) en buckets."""
    if not txt:
        return "Sin respuesta"
    s = str(txt).lower()
    if any(k in s for k in ["vocación", "vocacion", "pasión", "pasion", "siempre", "gusto", "encanta"]):
        return "Vocación personal"
    if any(k in s for k in ["laboral", "trabajo", "empleo", "ingreso", "mejor", "oportunidad"]):
        return "Mejora laboral"
    if any(k in s for k in ["familia", "padre", "madre", "hijo", "hija"]):
        return "Motivo familiar"
    if any(k in s for k in ["aporte", "comunidad", "social", "ayudar", "servir", "país", "pais"]):
        return "Aporte social"
    if any(k in s for k in ["emprend", "negocio", "empresa", "crear"]):
        return "Emprendimiento"
    if any(k in s for k in ["tecnolog", "innov", "desarrollo", "futuro"]):
        return "Tecnología/Innovación"
    if len(s) < 5:
        return "Sin respuesta"
    return "Otro"


def _cat_razon_institucion(txt):
    """Categoriza la razón de elegir IU Digital."""
    if not txt:
        return "Sin respuesta"
    s = str(txt).lower()
    if any(k in s for k in ["virtu", "online", "remoto", "digital"]):
        return "Virtualidad"
    if any(k in s for k in ["flexib", "horario", "tiempo"]):
        return "Flexibilidad"
    if any(k in s for k in ["costo", "precio", "económ", "economic", "barato"]):
        return "Costos"
    if any(k in s for k in ["recomend", "amigo", "conoc"]):
        return "Recomendación"
    if any(k in s for k in ["calidad", "acred", "prestig"]):
        return "Calidad/Acreditación"
    if any(k in s for k in ["public", "estat", "gratu", "becas"]):
        return "Pública/Becas"
    if len(s) < 3:
        return "Sin respuesta"
    return "Otro"


def _cat_hobbies(txt):
    """Devuelve lista de categorías de hobbies detectados."""
    if not txt:
        return []
    s = str(txt).lower()
    cats = set()
    if any(k in s for k in ["música", "musica", "cantar", "tocar", "instrumento", "guitarra", "piano"]):
        cats.add("Música")
    if any(k in s for k in ["leer", "lectura", "libro"]):
        cats.add("Lectura")
    if any(k in s for k in ["deport", "fútbol", "futbol", "ciclismo", "correr", "gimnasio", "natación", "natacion"]):
        cats.add("Deporte")
    if any(k in s for k in ["tecnolog", "computad", "video", "gaming", "programar"]):
        cats.add("Tecnología")
    if any(k in s for k in ["arte", "pintar", "dibujo", "fotograf", "baile", "danza"]):
        cats.add("Arte")
    if any(k in s for k in ["cocinar", "gastronom"]):
        cats.add("Gastronomía")
    if any(k in s for k in ["viajar", "viaje", "turismo"]):
        cats.add("Viajar")
    if any(k in s for k in ["familia", "compartir", "amigos"]):
        cats.add("Familia/Social")
    if not cats and len(s) > 3:
        cats.add("Otro")
    return list(cats)


def _cat_actividades(txt):
    """Categoriza C_strActividadesNoAcademicas."""
    if not txt:
        return []
    s = str(txt).lower()
    cats = set()
    if any(k in s for k in ["deport", "fútbol", "futbol", "atletismo"]):
        cats.add("Deportiva")
    if any(k in s for k in ["cultur", "música", "musica", "teatro", "danza"]):
        cats.add("Cultural")
    if any(k in s for k in ["emprend", "negocio", "empresa"]):
        cats.add("Emprendimiento")
    if any(k in s for k in ["voluntar", "social", "comunidad", "ayuda"]):
        cats.add("Voluntariado")
    if any(k in s for k in ["religios", "iglesia", "espiritu"]):
        cats.add("Religiosa")
    if any(k in s for k in ["acadé", "acade", "investig", "estudio"]):
        cats.add("Académica")
    if not cats and len(s) > 3:
        cats.add("Otra")
    return list(cats)


def _has_distinciones(txt):
    if not txt:
        return False
    s = str(txt).lower().strip()
    if len(s) < 3 or s in ("ninguno", "ninguna", "no", "n/a", "no aplica"):
        return False
    return True


def _norm_program(p):
    if not isinstance(p, str):
        return None
    return " ".join(p.strip().upper().split())


async def seed_students():
    if not EXCEL_PATH.exists():
        print("[seed] Excel demo no encontrado, omitiendo.")
        return
    count = await db.students.count_documents({})
    if count > 0:
        print(f"[seed] students ya cargados ({count}), omitiendo.")
        return
    print("[seed] Cargando estudiantes desde Excel...")
    df = pd.read_excel(EXCEL_PATH)
    df = df.fillna("")

    # Realistic Colombia-wide distribution for IU Digital (educación digital)
    # Two-step: pick department by weight, then pick municipality within department
    by_dept = {}
    for m in MUNICIPIOS:
        by_dept.setdefault(m["departamento"], []).append(m)

    weights = {
        "ANTIOQUIA": 45,
        "BOGOTA D.C.": 10,
        "CUNDINAMARCA": 5,
        "VALLE DEL CAUCA": 8,
        "ATLANTICO": 4,
        "BOLIVAR": 3,
        "SANTANDER": 4,
        "NORTE DE SANTANDER": 2,
        "CORDOBA": 2,
        "CALDAS": 2,
        "RISARALDA": 2,
        "QUINDIO": 1,
        "TOLIMA": 1,
        "HUILA": 1,
        "NARIÑO": 1,
        "CAUCA": 1,
        "MAGDALENA": 1,
        "CESAR": 1,
        "LA GUAJIRA": 1,
        "SUCRE": 1,
        "BOYACA": 1,
        "META": 1,
        "CHOCO": 1,
        "CASANARE": 1,
        "VENEZUELA": 1,
        "ECUADOR": 1,
        "PANAMA": 1,
        "ESTADOS UNIDOS": 1,
        "ESPAÑA": 1,
    }
    # Build a flat list where each entry is a department picked once per weight unit
    dept_pool = []
    for dept, w in weights.items():
        if by_dept.get(dept):
            dept_pool.extend([dept] * w)

    random.seed(42)

    docs = []
    PERIODO = "2025-2"
    for _, row in df.iterrows():
        cedula = str(row.get("Cédula", "")).strip()
        if not cedula:
            continue
        programa = _norm_program(row.get("Programa"))
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
            # Two-step: department by weight, then municipality within
            h = abs(hash(cedula))
            dept = dept_pool[h % len(dept_pool)]
            munis_in_dept = by_dept[dept]
            muni = munis_in_dept[(h // 1000) % len(munis_in_dept)]

        promedio = float(row.get("Promedio") or 0) or 0.0
        try:
            avance_total = float(row.get("Total") or 0)
            aprobadas = float(row.get("Aprobadas") or 0)
            avance_pct = (aprobadas / avance_total * 100.0) if avance_total else 0.0
        except Exception:
            avance_pct = 0.0

        # Edad calculada desde fecha de nacimiento
        edad = _calc_edad(row.get("P_strFechaNacimiento"))
        # Rango de ingresos
        ing = float(row.get("C_dblIngresosFlia") or 0)
        rango_ingresos = _rango_ingresos(ing)
        # Categorización de campos texto abierto
        razon_carrera_cat = _cat_razon_carrera(row.get("C_strRazonCarrera"))
        razon_institucion = _cat_razon_institucion(row.get("C_strRazonPresentacion"))
        hobbies_cat = _cat_hobbies(row.get("C_strHobbies"))
        actividades_cat = _cat_actividades(row.get("C_strActividadesNoAcademicas"))
        distinciones_flag = _has_distinciones(row.get("C_strDistinciones"))

        docs.append({
            "id": str(uuid.uuid4()),
            "cedula": cedula,
            "nombre": str(row.get("Nombre") or "").strip(),
            "apellidos": str(row.get("Apellidos") or "").strip(),
            "correo": str(row.get("Correo") or "").strip(),
            "telefono": str(row.get("Telefono") or "").strip(),
            "tipo_documento": str(row.get("P_idTipoDocumento") or "").strip().upper(),
            "fecha_nacimiento": str(row.get("P_strFechaNacimiento") or "").strip(),
            "edad": edad,
            "rango_edad": _rango_edad(edad),
            "programa": programa or "SIN PROGRAMA",
            "nivel": int(row.get("Nivel") or 0) if str(row.get("Nivel") or "").strip().isdigit() else 0,
            "estado_matricula": str(row.get("EstadoMatricula") or "").strip(),
            "estado": str(row.get("Estado") or "").strip(),
            "promedio": promedio,
            "total_materias": float(row.get("Total") or 0),
            "aprobadas": float(row.get("Aprobadas") or 0),
            "reprobadas": float(row.get("Reprobadas") or 0),
            "pendientes": float(row.get("Pendientes") or 0),
            "avance_pct": round(avance_pct, 2),
            "doble_matricula": _b(row.get("DobleMatricula")),
            "genero": str(row.get("P_idGenero") or "").strip().upper() or "NO INFORMA",
            "estrato": str(row.get("P_idEstrato") or "").strip().upper() or "SIN DATO",
            "estado_civil": str(row.get("P_idEstadoCivil") or "").strip().upper() or "NO INFORMA",
            "sisben_nivel": str(row.get("P_idSisben") or "").strip().upper() or "NO APLICA",
            "sisben_tiene": str(row.get("P_idSisben") or "").strip().lower() not in ("", "no aplica", "no", "ninguno", "ninguna"),
            "grupo_sisben": str(row.get("P_idGrupoSisben") or "").strip().upper() or "NO APLICA",
            "etnia": str(row.get("P_idEtnia") or "NO APLICA").strip().upper() or "NO APLICA",
            "etnia_institucional": str(row.get("C_idEtnia") or "").strip().upper(),
            "grupo_etnia": str(row.get("P_idGrupoEtnia") or "").strip(),
            "resguardo_indigena": _b(row.get("C_blnResguardoIndigena")),
            "discapacidad_flag": _b(row.get("C_blnTieneDiscapacidad")),
            "discapacidad_tipo": str(row.get("P_idDiscapacidad") or "").strip().upper() or "NINGUNA",
            "capacidad_excepcional": str(row.get("P_idCapacidad") or "").strip().upper() or "NINGUNA",
            "grupo_vulnerable": _b(row.get("C_blnGrupoVulnerable")),
            "tipo_grupo_vulnerable": str(row.get("C_strGrupoVulnerable") or "").strip().upper() or "NINGUNO",
            "victima_conflicto": str(row.get("C_intVictima") or "").strip().lower() in ("sí", "si"),
            "veterano": str(row.get("C_idVeterano") or "").strip().upper() or "NO APLICA",
            "tipo_ubicacion": str(row.get("C_idTipoUbicacion") or "").strip() or "SIN DATO",
            "zona_frontera": str(row.get("C_strCodigoPaisFrontera") or "").strip().upper() or "NO APLICA",
            "ingresos_flia": ing,
            "rango_ingresos": rango_ingresos,
            "num_personas_flia": int(float(row.get("C_intNumPersonasFlia") or 0)),
            "num_aportantes": int(float(row.get("C_intNumAportantes") or 0)),
            "hnos_educ_superior": int(float(row.get("C_intNumHnosEducSuperior") or 0)),
            "vivienda_propia": _b(row.get("C_intViviendaPropia")),
            "deuda_vivienda": _b(row.get("C_intDeudaVivienda")),
            "nivel_educ_madre": str(row.get("C_idNivel_estud_madre") or "").strip().upper() or "NO INFORMA",
            "nivel_educ_padre": str(row.get("C_idNivel_estud_padre") or "").strip().upper() or "NO INFORMA",
            "parentesco_emergencia": str(row.get("P_idParentesco") or "").strip().upper(),
            "razon_carrera_cat": razon_carrera_cat,
            "razon_institucion": razon_institucion,
            "hobbies_cat": hobbies_cat,
            "actividades_cat": actividades_cat,
            "tiene_distinciones": distinciones_flag,
            "ciudad_codigo": muni["codigo"],
            "ciudad_nombre": muni["nombre"],
            "departamento": muni["departamento"],
            "pais": "COLOMBIA" if muni["departamento"] not in ("VENEZUELA", "ECUADOR", "PANAMA", "ESTADOS UNIDOS", "ESPAÑA", "CHILE", "ARGENTINA", "MEXICO", "PERU") else muni["departamento"],
            "lat": muni["lat"],
            "lon": muni["lon"],
            "facultad": None,  # populated via catalog mapping later
            "periodo": PERIODO,
            "created_at": datetime.utcnow().isoformat(),
        })

    # Batched insert
    if docs:
        BATCH = 2000
        for i in range(0, len(docs), BATCH):
            await db.students.insert_many(docs[i:i + BATCH])
        print(f"[seed] {len(docs)} estudiantes insertados.")

    # Seed catalogs from data
    await _seed_catalogs_from_students()
    await _create_historical_demo()


async def _seed_catalogs_from_students():
    """Build facultades y programas según la estructura institucional oficial IU Digital de Antioquia."""
    # Mapeo OFICIAL (6 facultades) según portal institucional
    facultad_map = {
        # Facultad de Ciencias Administrativas y Económicas
        "ADMINISTRACIÓN DE EMPRESAS": "Facultad de Ciencias Administrativas y Económicas",
        "ADMINISTRACIÓN DE EMPRESAS TURÍSTICAS Y HOTELERAS": "Facultad de Ciencias Administrativas y Económicas",
        "ADMINISTRACIÓN EN SEGURIDAD Y SALUD EN EL TRABAJO": "Facultad de Ciencias Administrativas y Económicas",
        "ESPECIALIZACIÓN EN FORMULACIÓN Y EVALUACIÓN DE PROYECTOS": "Facultad de Ciencias Administrativas y Económicas",
        "ESPECIALIZACIÓN EN GERENCIA DE LA SEGURIDAD Y SALUD EN EL TRABAJO": "Facultad de Ciencias Administrativas y Económicas",
        "PUBLICIDAD Y MERCADEO DIGITAL": "Facultad de Ciencias Administrativas y Económicas",
        "TECNOLOGÍA EN GESTIÓN ADMINISTRATIVA": "Facultad de Ciencias Administrativas y Económicas",
        "TECNOLOGÍA EN GESTIÓN COMERCIAL AGROEMPRESARIAL": "Facultad de Ciencias Administrativas y Económicas",
        "TECNOLOGÍA EN GESTIÓN LOGÍSTICA PORTUARIA Y DEL TRANSPORTE": "Facultad de Ciencias Administrativas y Económicas",
        "FUNDAMENTOS DE ADMINISTRACIÓN Y EMPRENDIMIENTO PMDP GP02 TALENTO ESPECIALIZADO": "Facultad de Ciencias Administrativas y Económicas",
        # Facultad de Ciencias Ambientales
        "CIENCIAS AMBIENTALES": "Facultad de Ciencias Ambientales",
        "ESPECIALIZACIÓN EN GESTIÓN AMBIENTAL PARA EL DESARROLLO TERRITORIAL SOSTENIBLE": "Facultad de Ciencias Ambientales",
        # Facultad de Ciencias y Tecnologías Digitales
        "ESPECIALIZACIÓN EN ANALÍTICA Y BIG DATA": "Facultad de Ciencias y Tecnologías Digitales",
        "ESPECIALIZACIÓN EN PROGRAMACIÓN APLICADA": "Facultad de Ciencias y Tecnologías Digitales",
        "INGENIERÍA DE SOFTWARE Y DATOS": "Facultad de Ciencias y Tecnologías Digitales",
        "TECNOLOGÍA EN DESARROLLO DE SOFTWARE": "Facultad de Ciencias y Tecnologías Digitales",
        # Facultad de Ingeniería
        "ESPECIALIZACIÓN EN INOCUIDAD AGROALIMENTARIA": "Facultad de Ingeniería",
        "INGENIERÍA MECATRÓNICA": "Facultad de Ingeniería",
        "INGENIERÍA EN DESARROLLO TERRITORIAL": "Facultad de Ingeniería",
        "TECNOLOGIA EN GESTION CATASTRAL Y AGRIMENSURA": "Facultad de Ingeniería",
        # Facultad de Educación
        "ESPECIALIZACIÓN EN TECNOLOGÍAS DIGITALES PARA EL APRENDIZAJE": "Facultad de Educación",
        "LICENCIATURA EN EDUCACIÓN BÁSICA PRIMARIA": "Facultad de Educación",
        # Facultad de Ciencias Sociales y Humanas
        "TECNOLOGÍA EN DESARROLLO COMUNITARIO": "Facultad de Ciencias Sociales y Humanas",
        "TRABAJO SOCIAL": "Facultad de Ciencias Sociales y Humanas",
    }
    facultades = {}
    for prog, fac in facultad_map.items():
        if fac not in facultades:
            facultades[fac] = str(uuid.uuid4())
            await db.facultades.update_one(
                {"nombre": fac},
                {"$setOnInsert": {
                    "id": facultades[fac],
                    "nombre": fac,
                    "codigo": None,
                    "created_at": datetime.utcnow().isoformat(),
                }},
                upsert=True,
            )
        else:
            pass

    # Programs
    programas = await db.students.distinct("programa")
    for prog in programas:
        if not prog:
            continue
        fac_name = facultad_map.get(prog)
        if not fac_name:
            # Smart fallback by keyword
            p = prog.upper()
            if any(k in p for k in ["LICENCIATURA", "EDUCACIÓN BÁSICA", "EDUCACION BASICA", "PEDAGOG"]):
                fac_name = "Facultad de Educación"
            elif any(k in p for k in ["TRABAJO SOCIAL", "DESARROLLO COMUNITARIO", "CIENCIAS SOCIALES"]):
                fac_name = "Facultad de Ciencias Sociales y Humanas"
            elif any(k in p for k in ["AMBIENT", "BIOLOG"]):
                fac_name = "Facultad de Ciencias Ambientales"
            elif any(k in p for k in ["SOFTWARE", "DATOS", "PROGRAMAC", "DIGITAL"]) and "MERCADEO" not in p:
                fac_name = "Facultad de Ciencias y Tecnologías Digitales"
            elif any(k in p for k in ["INGENIER", "MECATRÓN", "MECATRON", "CATASTRAL", "INOCUIDAD"]):
                fac_name = "Facultad de Ingeniería"
            elif any(k in p for k in ["ADMINIST", "GESTIÓN", "GESTION", "EMPRES", "LOGÍS", "LOGIS", "AGROEMPRES", "EMPREND", "SEGURIDAD Y SALUD", "PUBLICIDAD", "MERCADEO", "PROYECT"]):
                fac_name = "Facultad de Ciencias Administrativas y Económicas"
            else:
                fac_name = "Facultad de Ciencias Administrativas y Económicas"
        fac_doc = await db.facultades.find_one({"nombre": fac_name}, {"_id": 0})
        if not fac_doc:
            new_id = str(uuid.uuid4())
            await db.facultades.insert_one({
                "id": new_id, "nombre": fac_name, "codigo": None,
                "created_at": datetime.utcnow().isoformat(),
            })
            fac_doc = {"id": new_id}
        await db.programas.update_one(
            {"nombre": prog},
            {"$setOnInsert": {
                "id": str(uuid.uuid4()),
                "nombre": prog,
                "codigo": None,
                "facultad_id": fac_doc["id"],
                "created_at": datetime.utcnow().isoformat(),
            }},
            upsert=True,
        )
        # update students with facultad name
        await db.students.update_many({"programa": prog}, {"$set": {"facultad": fac_name}})

    # Seed periodos (incluye 2026-1)
    for p in ["2024-1", "2024-2", "2025-1", "2025-2", "2026-1"]:
        await db.periodos.update_one(
            {"nombre": p},
            {"$setOnInsert": {
                "id": str(uuid.uuid4()),
                "nombre": p,
                "codigo": p,
                "created_at": datetime.utcnow().isoformat(),
            }},
            upsert=True,
        )

    print("[seed] Catálogos generados (facultades, programas, periodos).")
    await _seed_materias_and_docente_demo()


# Materias demo por programa (3 materias por programa)
MATERIAS_POR_PROGRAMA = {
    "default": ["Cátedra Institucional", "Metodología de la Investigación", "Comunicación y Lectoescritura"],
    "INGENIERÍA DE SOFTWARE Y DATOS": ["Programación I", "Estructuras de Datos", "Bases de Datos"],
    "INGENIERÍA MECATRÓNICA": ["Cálculo I", "Electrónica Básica", "Sistemas de Control"],
    "TECNOLOGÍA EN DESARROLLO DE SOFTWARE": ["Programación Web", "Algoritmos", "Ingeniería de Software"],
    "ADMINISTRACIÓN DE EMPRESAS": ["Contabilidad General", "Microeconomía", "Gestión Estratégica"],
    "TRABAJO SOCIAL": ["Fundamentos del Trabajo Social", "Política Social", "Intervención Comunitaria"],
    "PUBLICIDAD Y MERCADEO DIGITAL": ["Estrategia Digital", "Branding", "Analítica de Audiencias"],
    "CIENCIAS AMBIENTALES": ["Ecología General", "Gestión Ambiental", "Cambio Climático"],
    "LICENCIATURA EN EDUCACIÓN BÁSICA PRIMARIA": ["Didáctica General", "Psicología Educativa", "Pedagogía Crítica"],
    "ADMINISTRACIÓN EN SEGURIDAD Y SALUD EN EL TRABAJO": ["SG-SST", "Higiene Industrial", "Ergonomía"],
}


async def _seed_materias_and_docente_demo():
    """Create one materia per program and a demo docente user with assignments."""
    progs = await db.programas.find({}, {"_id": 0}).to_list(100)
    materias_created = 0
    for p in progs:
        nombres = MATERIAS_POR_PROGRAMA.get(p["nombre"], MATERIAS_POR_PROGRAMA["default"])
        for i, mat_nombre in enumerate(nombres):
            existing = await db.materias.find_one({"nombre": mat_nombre, "programa_id": p["id"]})
            if existing:
                continue
            await db.materias.insert_one({
                "id": str(uuid.uuid4()),
                "nombre": mat_nombre,
                "codigo": f"{p.get('codigo') or 'PRG'}-{i+1:02d}",
                "programa_id": p["id"],
                "facultad_id": p.get("facultad_id"),
                "created_at": datetime.utcnow().isoformat(),
            })
            materias_created += 1
    if materias_created:
        print(f"[seed] {materias_created} materias creadas.")

    # Create demo docente if not exists
    docente_email = "docente.demo@iudigital.edu.co"
    existing = await db.users.find_one({"email": docente_email})
    if not existing:
        from auth import hash_password as _hp
        docente_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": docente_id,
            "email": docente_email,
            "password": _hp("Docente2026!"),
            "full_name": "Prof. Ana María Restrepo",
            "role": "profesor",
            "active": True,
            "must_change_password": False,
            "created_at": datetime.utcnow().isoformat(),
        })
        print(f"[seed] Docente demo creado: {docente_email} / Docente2026!")
    else:
        docente_id = existing["id"]

    # Assign 4 materias spread across programs (Ingeniería Software, Admin, Trabajo Social, Publicidad)
    rel_count = await db.docente_materia.count_documents({"docente_id": docente_id})
    if rel_count == 0:
        target_progs = [
            "INGENIERÍA DE SOFTWARE Y DATOS",
            "ADMINISTRACIÓN DE EMPRESAS",
            "TRABAJO SOCIAL",
            "PUBLICIDAD Y MERCADEO DIGITAL",
        ]
        for prog_name in target_progs:
            prog = await db.programas.find_one({"nombre": prog_name}, {"_id": 0})
            if not prog:
                continue
            # Pick first materia of this program
            mat = await db.materias.find_one({"programa_id": prog["id"]}, {"_id": 0})
            if not mat:
                continue
            await db.docente_materia.insert_one({
                "id": str(uuid.uuid4()),
                "docente_id": docente_id,
                "facultad_id": prog.get("facultad_id"),
                "programa_id": prog["id"],
                "materia_id": mat["id"],
                "periodo": "2025-2",
                "created_at": datetime.utcnow().isoformat(),
            })
        print("[seed] 4 asignaciones docente-materia creadas para docente demo.")


async def _create_historical_demo():
    """Aggregate per-program historical snapshots for charts."""
    count = await db.historico.count_documents({})
    if count > 0:
        return
    progs = await db.students.distinct("programa")
    snapshots = []
    base_periodos = ["2024-1", "2024-2", "2025-1", "2025-2", "2026-1"]
    for prog in progs:
        if not prog:
            continue
        # Use real 2025-2 average from data
        pipeline = [{"$match": {"programa": prog}},
                    {"$group": {"_id": None, "avg": {"$avg": "$promedio"}, "tot": {"$sum": 1}}}]
        agg = await db.students.aggregate(pipeline).to_list(1)
        base_avg = (agg[0]["avg"] if agg else 3.5) or 3.5
        for i, per in enumerate(base_periodos):
            noise = (random.random() - 0.5) * 0.4
            snapshots.append({
                "id": str(uuid.uuid4()),
                "programa": prog,
                "periodo": per,
                "promedio": round(max(0, min(5, base_avg + (i - 3) * 0.05 + noise)), 2),
                "tasa_aprobacion": round(min(100, max(50, 78 + (i - 3) * 1.5 + noise * 20)), 1),
                "tasa_reprobacion": round(max(0, 22 - (i - 3) * 1.5 - noise * 20), 1),
                "matriculados": int((agg[0]["tot"] if agg else 100) * (0.9 + i * 0.05)),
            })
    if snapshots:
        await db.historico.insert_many(snapshots)
        print(f"[seed] Histórico demo creado ({len(snapshots)} snapshots).")
