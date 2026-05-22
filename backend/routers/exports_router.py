"""Export endpoints: students, dashboards data as Excel/CSV."""
import io
from datetime import datetime
import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from auth import get_current_user
from database import db

router = APIRouter(prefix="/api/exports", tags=["exports"])


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


async def _apply_docente_materia(match: dict, docente_id, materia_id) -> dict:
    if not docente_id and not materia_id:
        return match
    hn_match = {}
    if docente_id and docente_id not in ("all", "todos", ""):
        hn_match["docente_id"] = docente_id
    if materia_id and materia_id not in ("all", "todos", ""):
        hn_match["materia_id"] = materia_id
    if hn_match:
        cedulas = await db.historico_notas.distinct("cedula", hn_match)
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
    user=Depends(get_current_user),
):
    """Descarga la base completa de estudiantes según filtros aplicados."""
    match = _build_match(locals())
    match = await _apply_docente_materia(match, docente_id, materia_id)
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
    user=Depends(get_current_user),
):
    """Descarga histórico de notas con filtros opcionales."""
    m = {}
    if periodo and periodo != "all":
        m["periodo"] = periodo
    if docente_id and docente_id != "all":
        m["docente_id"] = docente_id
    if materia_id and materia_id != "all":
        m["materia_id"] = materia_id
    docs = await db.historico_notas.find(m, {"_id": 0, "id": 0, "created_at": 0, "upload_id": 0}).to_list(100000)
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
