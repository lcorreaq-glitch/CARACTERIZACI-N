"""Export endpoints: students, dashboards data as Excel/CSV."""
import io
from datetime import datetime
import pandas as pd
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from auth import get_current_user
from database import db
from scope import apply_role_scope

router = APIRouter(prefix="/api/exports", tags=["exports"])


async def _can_download(user) -> bool:
    """Descargas: superadmin/direccion siempre; decano/coordinador/profesor requieren permiso individual
    o el toggle global (docente_downloads_globally_enabled)."""
    role = user.get("role")
    if role in ("superadmin", "direccion"):
        return True
    if role in ("profesor", "decano", "coordinador"):
        if user.get("download_enabled") is True:
            return True
        settings = await db.system_settings.find_one({"_id": "global"}, {"_id": 0}) or {}
        return bool(settings.get("docente_downloads_globally_enabled", False))
    return False


async def _enforce_download(user):
    if not await _can_download(user):
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso de descarga. Contacte al administrador.",
        )


async def _enforce_docente_scope(user, codigo_grupo: Optional[str], docente_id: Optional[str]):
    """A docente can only export their own groups."""
    if user.get("role") != "profesor":
        return
    if codigo_grupo:
        g = await db.grupos.find_one({"codigo_grupo": codigo_grupo}, {"_id": 0, "docente_id": 1})
        if not g or g.get("docente_id") != user["id"]:
            raise HTTPException(403, "No puede exportar grupos de otros docentes")
    elif docente_id and docente_id != user["id"]:
        raise HTTPException(403, "No puede exportar datos de otros docentes")


def _build_match(args):
    m = {}
    mapping = {
        "periodo": "periodo", "facultad": "facultad", "programa": "programa",
        "genero": "genero", "estrato": "estrato", "etnia": "etnia",
        "tipo_ubicacion": "tipo_ubicacion", "estado_matricula": "estado_matricula",
        "departamento": "departamento",
    }
    for k, field in mapping.items():
        v = args.get(k)
        if v not in (None, "", "all"):
            m[field] = v
    for k, field in {"sisben": "sisben_tiene", "discapacidad": "discapacidad_flag",
                     "victima": "victima_conflicto", "grupo_vulnerable": "grupo_vulnerable"}.items():
        v = args.get(k)
        if v in ("true", "1", True):
            m[field] = True
    return m


async def _apply_docente_materia(match: dict, docente_id, materia_id, codigo_grupo=None) -> dict:
    if not docente_id and not materia_id and not codigo_grupo:
        return match
    # Si hay codigo_grupo, filtrar por matriculas del grupo específico
    if codigo_grupo and codigo_grupo not in ("all", "todos", ""):
        cedulas = await db.matriculas.distinct("cedula", {"codigo_grupo": codigo_grupo})
        match["cedula"] = {"$in": cedulas} if cedulas else "__NO_MATCH__"
        return match
    # Filtrado por docente y/o materia
    if docente_id and docente_id not in ("all", "todos", ""):
        # Solo matrículas activas del docente (no incluye histórico de periodos anteriores)
        cedulas = await db.matriculas.distinct("cedula", {"docente_id": docente_id})
        if materia_id and materia_id not in ("all", "todos", ""):
            # Intersección con materia
            cedulas_materia = await db.historico_notas.distinct("cedula", {"materia_id": materia_id})
            cedulas = list(set(cedulas) & set(cedulas_materia))
        match["cedula"] = {"$in": cedulas} if cedulas else "__NO_MATCH__"
        return match
    if materia_id and materia_id not in ("all", "todos", ""):
        cedulas = await db.historico_notas.distinct("cedula", {"materia_id": materia_id})
        match["cedula"] = {"$in": cedulas} if cedulas else "__NO_MATCH__"
    return match


def _stream_xlsx(df: pd.DataFrame, sheet_name: str = "Datos", filename: str = "export.xlsx"):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _stream_csv(df: pd.DataFrame, filename: str = "export.csv"):
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/students")
async def export_students(
    fmt: str = Query("xlsx", regex="^(xlsx|csv)$"),
    periodo: Optional[str] = None,
    facultad: Optional[str] = None,
    programa: Optional[str] = None,
    genero: Optional[str] = None,
    estrato: Optional[str] = None,
    etnia: Optional[str] = None,
    tipo_ubicacion: Optional[str] = None,
    estado_matricula: Optional[str] = None,
    departamento: Optional[str] = None,
    sisben: Optional[str] = None,
    discapacidad: Optional[str] = None,
    victima: Optional[str] = None,
    grupo_vulnerable: Optional[str] = None,
    docente_id: Optional[str] = None,
    materia_id: Optional[str] = None,
    codigo_grupo: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Descarga la base completa de estudiantes según filtros aplicados."""
    await _enforce_download(user)
    await _enforce_docente_scope(user, codigo_grupo, docente_id)
    # Force docente scope
    if user.get("role") == "profesor" and not codigo_grupo and not docente_id:
        docente_id = user["id"]
    match = _build_match(locals())
    match = await _apply_docente_materia(match, docente_id, materia_id, codigo_grupo)
    match = apply_role_scope(user, match)
    cursor = db.students.find(match, {"_id": 0, "id": 0, "created_at": 0,
                                       "hobbies_cat": 0, "actividades_cat": 0,
                                       "lat": 0, "lon": 0})
    docs = await cursor.to_list(50000)
    if not docs:
        docs = [{"info": "Sin datos con los filtros aplicados"}]
    df = pd.DataFrame(docs)
    ts = datetime.utcnow().strftime("%Y%m%d")
    fname = f"estudiantes_iudigital_{ts}.{fmt}"
    return _stream_xlsx(df, "Estudiantes", fname) if fmt == "xlsx" else _stream_csv(df, fname)


@router.get("/dashboard/{scope}")
async def export_dashboard(
    scope: str,
    fmt: str = Query("xlsx", regex="^(xlsx|csv)$"),
    periodo: Optional[str] = None,
    facultad: Optional[str] = None,
    programa: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Exporta agregados del dashboard solicitado."""
    match = _build_match(locals())
    ts = datetime.utcnow().strftime("%Y%m%d")
    sheets = {}

    if scope in ("ejecutivo", "executive"):
        sheets["Por programa"] = await db.students.aggregate([
            {"$match": match}, {"$group": {"_id": "$programa", "estudiantes": {"$sum": 1}, "promedio": {"$avg": "$promedio"}}},
            {"$project": {"_id": 0, "programa": "$_id", "estudiantes": 1, "promedio": {"$round": ["$promedio", 2]}}},
            {"$sort": {"estudiantes": -1}},
        ]).to_list(100)
        sheets["Por género"] = await db.students.aggregate([
            {"$match": match}, {"$group": {"_id": "$genero", "n": {"$sum": 1}}},
            {"$project": {"_id": 0, "genero": "$_id", "n": 1}},
        ]).to_list(20)
        sheets["Por estrato"] = await db.students.aggregate([
            {"$match": match}, {"$group": {"_id": "$estrato", "n": {"$sum": 1}}},
            {"$sort": {"_id": 1}}, {"$project": {"_id": 0, "estrato": "$_id", "n": 1}},
        ]).to_list(20)
    elif scope == "academico":
        sheets["Por programa"] = await db.students.aggregate([
            {"$match": match}, {"$group": {
                "_id": "$programa", "n": {"$sum": 1},
                "promedio": {"$avg": "$promedio"},
                "aprobadas": {"$avg": "$aprobadas"},
                "reprobadas": {"$avg": "$reprobadas"},
                "avance_pct": {"$avg": "$avance_pct"},
            }},
            {"$project": {"_id": 0, "programa": "$_id", "n": 1,
                          "promedio": {"$round": ["$promedio", 2]},
                          "aprobadas": {"$round": ["$aprobadas", 1]},
                          "reprobadas": {"$round": ["$reprobadas", 1]},
                          "avance_pct": {"$round": ["$avance_pct", 1]}}},
            {"$sort": {"n": -1}},
        ]).to_list(100)
    elif scope == "territorial":
        sheets["Por municipio"] = await db.students.aggregate([
            {"$match": match},
            {"$group": {"_id": {"municipio": "$ciudad_nombre", "departamento": "$departamento", "pais": {"$ifNull": ["$pais", "COLOMBIA"]}},
                        "n": {"$sum": 1}, "promedio": {"$avg": "$promedio"}}},
            {"$project": {"_id": 0, "municipio": "$_id.municipio", "departamento": "$_id.departamento",
                          "pais": "$_id.pais", "n": 1, "promedio": {"$round": ["$promedio", 2]}}},
            {"$sort": {"n": -1}},
        ]).to_list(2000)
    elif scope == "caracterizacion":
        # 1 hoja por dimensión clave
        for dim, field in [("Género", "genero"), ("Estrato", "estrato"),
                           ("Rango edad", "rango_edad"), ("Rango ingresos", "rango_ingresos"),
                           ("Nivel educ. madre", "nivel_educ_madre"), ("Nivel educ. padre", "nivel_educ_padre"),
                           ("Etnia", "etnia"), ("Tipo ubicación", "tipo_ubicacion"),
                           ("Vulnerabilidad", "tipo_grupo_vulnerable"), ("Razón carrera", "razon_carrera_cat"),
                           ("Razón institución", "razon_institucion")]:
            sheets[dim] = await db.students.aggregate([
                {"$match": match}, {"$group": {"_id": f"${field}", "n": {"$sum": 1}}},
                {"$sort": {"n": -1}}, {"$project": {"_id": 0, dim: "$_id", "n": 1}},
            ]).to_list(50)
    else:
        sheets["Info"] = [{"error": f"scope '{scope}' no soportado"}]

    fname = f"dashboard_{scope}_{ts}.{fmt}"
    if fmt == "xlsx":
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            for name, rows in sheets.items():
                df = pd.DataFrame(rows or [{"info": "Sin datos"}])
                df.to_excel(writer, sheet_name=name[:31], index=False)
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers={"Content-Disposition": f'attachment; filename="{fname}"'})
    else:
        # CSV: solo primera hoja
        first = next(iter(sheets.values()))
        df = pd.DataFrame(first or [{"info": "Sin datos"}])
        return _stream_csv(df, fname)


@router.get("/divipola")
async def export_divipola(fmt: str = Query("xlsx", regex="^(xlsx|csv)$"), user=Depends(get_current_user)):
    items = await db.divipola_municipios.find({}, {"_id": 0, "id": 0}).to_list(5000)
    df = pd.DataFrame(items)
    ts = datetime.utcnow().strftime("%Y%m%d")
    fname = f"divipola_{ts}.{fmt}"
    return _stream_xlsx(df, "DIVIPOLA", fname) if fmt == "xlsx" else _stream_csv(df, fname)



@router.get("/notas")
async def export_notas(
    fmt: str = Query("xlsx", regex="^(xlsx|csv)$"),
    periodo: Optional[str] = None,
    docente_id: Optional[str] = None,
    materia_id: Optional[str] = None,
    codigo_grupo: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Descarga histórico de notas con filtros opcionales."""
    await _enforce_download(user)
    await _enforce_docente_scope(user, codigo_grupo, docente_id)
    if user.get("role") == "profesor" and not codigo_grupo and not docente_id:
        docente_id = user["id"]
    m = {}
    if periodo and periodo != "all":
        m["periodo"] = periodo
    if docente_id and docente_id != "all":
        m["docente_id"] = docente_id
    if materia_id and materia_id != "all":
        m["materia_id"] = materia_id
    if codigo_grupo and codigo_grupo != "all":
        m["codigo_grupo"] = codigo_grupo
    docs = await db.historico_notas.find(m, {"_id": 0, "id": 0, "created_at": 0, "upload_id": 0}).to_list(100000)
    # Role scope: filter by facultad/programa via cedulas of matching students
    scope_match = apply_role_scope(user, {})
    if "_no_scope_" in scope_match:
        docs = []
    elif "facultad" in scope_match or "programa" in scope_match:
        cedulas_scope = set(await db.students.distinct("cedula", scope_match))
        docs = [d for d in docs if d.get("cedula") in cedulas_scope]
    if not docs:
        docs = [{"info": "Sin notas registradas"}]
    df = pd.DataFrame(docs)
    ts = datetime.utcnow().strftime("%Y%m%d")
    fname = f"notas_iudigital_{ts}.{fmt}"
    return _stream_xlsx(df, "Notas", fname) if fmt == "xlsx" else _stream_csv(df, fname)


@router.get("/docente-materia")
async def export_docente_materia(fmt: str = Query("xlsx", regex="^(xlsx|csv)$"), user=Depends(get_current_user)):
    """Descarga catálogo docente-materia enriquecido con nombres."""
    rows = await db.docente_materia.find({}, {"_id": 0}).to_list(10000)
    out = []
    for r in rows:
        u = await db.users.find_one({"id": r.get("docente_id")}, {"_id": 0, "full_name": 1, "email": 1}) or {}
        mat = await db.materias.find_one({"id": r.get("materia_id")}, {"_id": 0, "nombre": 1, "codigo": 1}) or {}
        out.append({
            "EmailDocente": u.get("email", ""),
            "NombreDocente": u.get("full_name", ""),
            "CodigoMateria": mat.get("codigo", ""),
            "NombreMateria": mat.get("nombre", ""),
            "Periodo": r.get("periodo", ""),
        })
    if not out:
        out = [{"info": "Sin relaciones registradas"}]
    df = pd.DataFrame(out)
    ts = datetime.utcnow().strftime("%Y%m%d")
    fname = f"docente_materia_{ts}.{fmt}"
    return _stream_xlsx(df, "DocenteMateria", fname) if fmt == "xlsx" else _stream_csv(df, fname)



@router.get("/grupo/{codigo_grupo}")
async def export_grupo_detail(
    codigo_grupo: str,
    fmt: str = Query("xlsx", regex="^(xlsx|csv)$"),
    user=Depends(get_current_user),
):
    """Descarga el detalle completo de un grupo (cruce asignación × caracterización × notas).
    Un docente solo puede descargar sus propios grupos y requiere permiso habilitado."""
    await _enforce_download(user)
    await _enforce_docente_scope(user, codigo_grupo, None)

    grupo = await db.grupos.find_one({"codigo_grupo": codigo_grupo}, {"_id": 0})
    if not grupo:
        raise HTTPException(404, "Grupo no encontrado")

    # Role scope: decano/coordinador can only access groups within their facultad/programa
    scope_match = apply_role_scope(user, {})
    if "_no_scope_" in scope_match:
        raise HTTPException(403, "Su rol requiere facultad/programa asignado (contacte al administrador)")
    if "facultad" in scope_match or "programa" in scope_match:
        cedulas_grupo = await db.matriculas.distinct("cedula", {"codigo_grupo": codigo_grupo})
        if cedulas_grupo:
            in_scope = await db.students.count_documents({**scope_match, "cedula": {"$in": cedulas_grupo}})
            if in_scope == 0:
                raise HTTPException(403, "Este grupo no pertenece a su facultad/programa")

    # 1) Metadata del grupo
    resumen = [{
        "Código grupo": grupo.get("codigo_grupo"),
        "Asignatura": grupo.get("asignatura_nombre"),
        "Código asignatura": grupo.get("asignatura_codigo"),
        "Docente": grupo.get("docente_nombre"),
        "Cédula docente": grupo.get("docente_cedula"),
        "Email docente": grupo.get("docente_email"),
        "Programa": grupo.get("programa"),
        "Facultad": grupo.get("facultad"),
        "Periodo": grupo.get("periodo"),
        "Día": grupo.get("dia"),
        "Hora": grupo.get("hora"),
        "Bloque": grupo.get("bloque"),
    }]

    # 2) Matriculados
    matriculas = await db.matriculas.find(
        {"codigo_grupo": codigo_grupo}, {"_id": 0}
    ).to_list(2000)
    cedulas = [m["cedula"] for m in matriculas]

    # 3) Estudiantes con caracterización completa
    estudiantes_df = []
    if cedulas:
        est_docs = await db.students.find(
            {"cedula": {"$in": cedulas}},
            {"_id": 0, "id": 0, "created_at": 0, "hobbies_cat": 0,
             "actividades_cat": 0, "lat": 0, "lon": 0},
        ).to_list(2000)
        est_map = {e["cedula"]: e for e in est_docs}
        for m in matriculas:
            e = est_map.get(m["cedula"], {})
            estudiantes_df.append({
                **e,
                "estado_matricula": m.get("estado"),
            })

    # 4) Notas históricas del grupo (por cédula del grupo + asignatura del grupo)
    notas_docs = []
    if cedulas and grupo.get("asignatura_codigo"):
        notas_docs = await db.historico_notas.find(
            {"cedula": {"$in": cedulas},
             "codigo_asignatura": grupo["asignatura_codigo"]},
            {"_id": 0, "id": 0, "created_at": 0, "upload_id": 0},
        ).to_list(5000)

    ts = datetime.utcnow().strftime("%Y%m%d")
    fname = f"grupo_{codigo_grupo}_{ts}.{fmt}"

    if fmt == "csv":
        # CSV: solo estudiantes
        df = pd.DataFrame(estudiantes_df or [{"info": "Sin estudiantes matriculados"}])
        return _stream_csv(df, fname)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(resumen).to_excel(writer, sheet_name="Grupo", index=False)
        pd.DataFrame(estudiantes_df or [{"info": "Sin estudiantes"}]).to_excel(
            writer, sheet_name="Estudiantes", index=False
        )
        pd.DataFrame(notas_docs or [{"info": "Sin notas registradas"}]).to_excel(
            writer, sheet_name="Notas", index=False
        )
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/grupo/{codigo_grupo}/vista")
async def export_grupo_vista(
    codigo_grupo: str,
    fmt: str = Query("xlsx", regex="^(xlsx|csv)$"),
    user=Depends(get_current_user),
):
    """Descarga SOLO los datos que se ven en la vista del docente (matriculados + flags de vulnerabilidad).
    No incluye caracterización completa ni notas históricas."""
    await _enforce_download(user)
    await _enforce_docente_scope(user, codigo_grupo, None)

    grupo = await db.grupos.find_one({"codigo_grupo": codigo_grupo}, {"_id": 0})
    if not grupo:
        raise HTTPException(404, "Grupo no encontrado")

    scope_match = apply_role_scope(user, {})
    if "_no_scope_" in scope_match:
        raise HTTPException(403, "Su rol requiere facultad/programa asignado")
    if "facultad" in scope_match or "programa" in scope_match:
        cedulas_grupo = await db.matriculas.distinct("cedula", {"codigo_grupo": codigo_grupo})
        if cedulas_grupo:
            in_scope = await db.students.count_documents({**scope_match, "cedula": {"$in": cedulas_grupo}})
            if in_scope == 0:
                raise HTTPException(403, "Este grupo no pertenece a su facultad/programa")

    matriculas = await db.matriculas.find(
        {"codigo_grupo": codigo_grupo}, {"_id": 0, "cedula": 1, "estado": 1}
    ).to_list(2000)
    cedulas = [m["cedula"] for m in matriculas]

    rows = []
    if cedulas:
        est_docs = await db.students.find(
            {"cedula": {"$in": cedulas}},
            {"_id": 0, "cedula": 1, "nombre": 1, "apellidos": 1, "programa": 1,
             "promedio": 1, "sisben_tiene": 1, "sisben_nivel": 1,
             "grupo_vulnerable": 1, "tipo_grupo_vulnerable": 1,
             "victima_conflicto": 1, "tipo_ubicacion": 1,
             "discapacidad_flag": 1, "discapacidad_tipo": 1,
             "etnia": 1},
        ).to_list(2000)
        est_map = {e["cedula"]: e for e in est_docs}
        for m in matriculas:
            e = est_map.get(m["cedula"], {})
            flags = []
            if e.get("grupo_vulnerable"):
                flags.append(e.get("tipo_grupo_vulnerable") or "Vulnerable")
            if e.get("victima_conflicto"):
                flags.append("Víctima del conflicto")
            if e.get("discapacidad_flag"):
                flags.append(f"Discapacidad: {e.get('discapacidad_tipo') or 'No especificada'}")
            if e.get("sisben_tiene") and e.get("sisben_nivel"):
                flags.append(f"SISBEN {e.get('sisben_nivel')}")
            if e.get("tipo_ubicacion") in ("Rural", "Semirural"):
                flags.append(e.get("tipo_ubicacion"))
            if e.get("etnia") and e.get("etnia") not in ("Ninguno", "No Aplica"):
                flags.append(f"Etnia: {e.get('etnia')}")

            rows.append({
                "Cedula": m["cedula"],
                "Nombre": e.get("nombre", ""),
                "Apellidos": e.get("apellidos", ""),
                "Programa": e.get("programa", ""),
                "Promedio": e.get("promedio", 0) or 0,
                "Estado matricula": m.get("estado", ""),
                "Flags de vulnerabilidad": " | ".join(flags) if flags else "Sin flags",
                "N flags": len(flags),
            })

    ts = datetime.utcnow().strftime("%Y%m%d")
    fname = f"grupo_{codigo_grupo}_vista_{ts}.{fmt}"

    if not rows:
        rows = [{"info": "Sin estudiantes matriculados"}]

    df = pd.DataFrame(rows)
    if fmt == "csv":
        return _stream_csv(df, fname)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        resumen = [{
            "Codigo grupo": grupo.get("codigo_grupo"),
            "Asignatura": grupo.get("asignatura_nombre"),
            "Docente": grupo.get("docente_nombre"),
            "Programa": grupo.get("programa"),
            "Periodo": grupo.get("periodo"),
            "Total matriculados": len([r for r in rows if "Cedula" in r]),
        }]
        pd.DataFrame(resumen).to_excel(writer, sheet_name="Grupo", index=False)
        df.to_excel(writer, sheet_name="Vista docente", index=False)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )




@router.get("/permission")
async def download_permission(user=Depends(get_current_user)):
    """Endpoint público para el frontend: dice si el usuario actual puede descargar."""
    return {"can_download": await _can_download(user), "role": user.get("role")}
