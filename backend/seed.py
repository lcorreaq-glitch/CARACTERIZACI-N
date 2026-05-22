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

        docs.append({
            "id": str(uuid.uuid4()),
            "cedula": cedula,
            "nombre": str(row.get("Nombre") or "").strip(),
            "apellidos": str(row.get("Apellidos") or "").strip(),
            "correo": str(row.get("Correo") or "").strip(),
            "telefono": str(row.get("Telefono") or "").strip(),
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
            "genero": str(row.get("P_idGenero") or "").strip().upper() or "NO INFORMA",
            "estrato": str(row.get("P_idEstrato") or "").strip().upper() or "SIN DATO",
            "estado_civil": str(row.get("P_idEstadoCivil") or "").strip(),
            "sisben_tiene": _b(row.get("P_idSisben")),
            "grupo_sisben": str(row.get("P_idGrupoSisben") or "").strip(),
            "etnia": str(row.get("P_idEtnia") or "NO APLICA").strip().upper() or "NO APLICA",
            "discapacidad_flag": _b(row.get("C_blnTieneDiscapacidad")),
            "discapacidad_tipo": str(row.get("P_idDiscapacidad") or "").strip(),
            "grupo_vulnerable": _b(row.get("C_blnGrupoVulnerable")),
            "tipo_grupo_vulnerable": str(row.get("C_strGrupoVulnerable") or "").strip(),
            "victima_conflicto": str(row.get("C_intVictima") or "").strip().lower() in ("sí", "si"),
            "tipo_ubicacion": str(row.get("C_idTipoUbicacion") or "").strip(),
            "ingresos_flia": float(row.get("C_dblIngresosFlia") or 0),
            "num_personas_flia": float(row.get("C_intNumPersonasFlia") or 0),
            "vivienda_propia": _b(row.get("C_intViviendaPropia")),
            "ciudad_codigo": muni["codigo"],
            "ciudad_nombre": muni["nombre"],
            "departamento": muni["departamento"],
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
    """Build facultades and programas catalogs from student data."""
    facultad_map = {
        "ADMINISTRACIÓN DE EMPRESAS": "Facultad de Ciencias Económicas y Administrativas",
        "ADMINISTRACIÓN EN SEGURIDAD Y SALUD EN EL TRABAJO": "Facultad de Ciencias Económicas y Administrativas",
        "ADMINISTRACIÓN DE EMPRESAS TURÍSTICAS Y HOTELERAS": "Facultad de Ciencias Económicas y Administrativas",
        "PUBLICIDAD Y MERCADEO DIGITAL": "Facultad de Ciencias Económicas y Administrativas",
        "TECNOLOGÍA EN GESTIÓN ADMINISTRATIVA": "Facultad de Ciencias Económicas y Administrativas",
        "TECNOLOGÍA EN GESTIÓN LOGÍSTICA PORTUARIA Y DEL TRANSPORTE": "Facultad de Ciencias Económicas y Administrativas",
        "TECNOLOGÍA EN GESTIÓN COMERCIAL AGROEMPRESARIAL": "Facultad de Ciencias Económicas y Administrativas",
        "TRABAJO SOCIAL": "Facultad de Ciencias Sociales y Humanas",
        "LICENCIATURA EN EDUCACIÓN BÁSICA PRIMARIA": "Facultad de Ciencias Sociales y Humanas",
        "TECNOLOGÍA EN DESARROLLO COMUNITARIO": "Facultad de Ciencias Sociales y Humanas",
        "INGENIERÍA DE SOFTWARE Y DATOS": "Facultad de Ingenierías",
        "INGENIERÍA MECATRÓNICA": "Facultad de Ingenierías",
        "INGENIERÍA EN DESARROLLO TERRITORIAL": "Facultad de Ingenierías",
        "TECNOLOGÍA EN DESARROLLO DE SOFTWARE": "Facultad de Ingenierías",
        "TECNOLOGIA EN GESTION CATASTRAL Y AGRIMENSURA": "Facultad de Ingenierías",
        "CIENCIAS AMBIENTALES": "Facultad de Ingenierías",
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
        fac_name = facultad_map.get(prog, "Facultad General")
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

    # Seed periodos
    for p in ["2024-1", "2024-2", "2025-1", "2025-2"]:
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
            "role": "docente",
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
    base_periodos = ["2024-1", "2024-2", "2025-1", "2025-2"]
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
