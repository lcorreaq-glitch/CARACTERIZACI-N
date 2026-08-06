"""Admin router: users, facultades, programas, materias, periodos, docente-materia."""
from datetime import datetime
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException
from models import UserCreate, UserUpdate, CatalogIn, DocenteMateriaIn
from auth import hash_password, get_current_user, require_roles
from database import db

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def _enrich_users_with_scope_names(users):
    """Añade facultad_nombre/programa_nombre a cada usuario para la UI."""
    fac_ids = {u.get("facultad_id") for u in users if u.get("facultad_id")}
    prog_ids = {u.get("programa_id") for u in users if u.get("programa_id")}
    fac_map = {}
    prog_map = {}
    if fac_ids:
        async for f in db.facultades.find({"id": {"$in": list(fac_ids)}}, {"_id": 0, "id": 1, "nombre": 1}):
            fac_map[f["id"]] = f.get("nombre")
    if prog_ids:
        async for p in db.programas.find({"id": {"$in": list(prog_ids)}}, {"_id": 0, "id": 1, "nombre": 1}):
            prog_map[p["id"]] = p.get("nombre")
    for u in users:
        u["facultad_nombre"] = fac_map.get(u.get("facultad_id"))
        u["programa_nombre"] = prog_map.get(u.get("programa_id"))
    return users


def _validate_scope_assignment(role: str, facultad_id: Optional[str], programa_id: Optional[str]):
    """Enforce that decano/coordinador have the required scope assigned."""
    if role == "decano" and not facultad_id:
        raise HTTPException(400, "El rol 'decano' requiere una facultad asignada")
    if role == "coordinador" and not facultad_id and not programa_id:
        raise HTTPException(400, "El rol 'coordinador' requiere una facultad o un programa asignado")


# ---------- Users ----------
@router.get("/users")
async def list_users(user=Depends(require_roles("superadmin", "direccion"))):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    await _enrich_users_with_scope_names(users)
    return users


@router.post("/users")
async def create_user(payload: UserCreate, user=Depends(require_roles("superadmin"))):
    if await db.users.find_one({"email": payload.email.lower()}):
        raise HTTPException(400, "Email ya existe")
    _validate_scope_assignment(payload.role, payload.facultad_id, payload.programa_id)
    new = {
        "id": str(uuid.uuid4()),
        "email": payload.email.lower(),
        "password": hash_password(payload.password),
        "full_name": payload.full_name,
        "role": payload.role,
        "facultad_id": payload.facultad_id,
        "programa_id": payload.programa_id,
        "active": True,
        "must_change_password": True,
        "download_enabled": payload.role in ("superadmin", "direccion"),
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.users.insert_one(new)
    new.pop("password", None)
    new.pop("_id", None)
    return new


@router.patch("/users/{user_id}")
async def update_user(user_id: str, payload: UserUpdate, user=Depends(require_roles("superadmin"))):
    upd = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not upd:
        raise HTTPException(400, "Nada que actualizar")
    # If role/scope is being updated, validate the combined resulting state
    existing = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Usuario no encontrado")
    merged = {**existing, **upd}
    if merged.get("role") in ("decano", "coordinador"):
        _validate_scope_assignment(merged["role"], merged.get("facultad_id"), merged.get("programa_id"))
    await db.users.update_one({"id": user_id}, {"$set": upd})
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return u


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user=Depends(require_roles("superadmin"))):
    if user_id == user["id"]:
        raise HTTPException(400, "No puedes eliminar tu propio usuario")
    await db.users.delete_one({"id": user_id})
    return {"ok": True}


@router.post("/users/{user_id}/toggle-active")
async def toggle_active(user_id: str, user=Depends(require_roles("superadmin"))):
    if user_id == user["id"]:
        raise HTTPException(400, "No puedes desactivar tu propio usuario")
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "active": 1})
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    new_state = not u.get("active", True)
    await db.users.update_one({"id": user_id}, {"$set": {"active": new_state}})
    return {"ok": True, "active": new_state}


@router.post("/users/{user_id}/toggle-download")
async def toggle_download(user_id: str, user=Depends(require_roles("superadmin"))):
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "download_enabled": 1})
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    new_state = not u.get("download_enabled", False)
    await db.users.update_one({"id": user_id}, {"$set": {"download_enabled": new_state}})
    return {"ok": True, "download_enabled": new_state}


@router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: str, payload: dict, user=Depends(require_roles("superadmin"))):
    new_password = (payload or {}).get("new_password") or "IUDigital2026!"
    if len(new_password) < 6:
        raise HTTPException(400, "La contraseña debe tener al menos 6 caracteres")
    r = await db.users.update_one(
        {"id": user_id},
        {"$set": {"password": hash_password(new_password), "must_change_password": True}},
    )
    if not r.matched_count:
        raise HTTPException(404, "Usuario no encontrado")
    return {"ok": True, "message": "Contraseña reseteada", "new_password": new_password}


# ---------- System settings (global permissions/toggles) ----------
DEFAULT_SETTINGS = {
    "docente_downloads_globally_enabled": False,
    "docente_ai_insights_enabled": True,
    "docente_can_see_all_periods": False,
    "allow_public_landing": False,
}


@router.get("/system-settings")
async def get_system_settings(user=Depends(require_roles("superadmin", "direccion"))):
    doc = await db.system_settings.find_one({"_id": "global"}, {"_id": 0}) or {}
    return {**DEFAULT_SETTINGS, **doc}


@router.patch("/system-settings")
async def update_system_settings(payload: dict, user=Depends(require_roles("superadmin"))):
    allowed = set(DEFAULT_SETTINGS.keys())
    upd = {k: bool(v) for k, v in (payload or {}).items() if k in allowed}
    if not upd:
        raise HTTPException(400, "Nada que actualizar")
    upd["updated_at"] = datetime.utcnow().isoformat()
    upd["updated_by"] = user.get("email")
    await db.system_settings.update_one(
        {"_id": "global"}, {"$set": upd}, upsert=True
    )
    doc = await db.system_settings.find_one({"_id": "global"}, {"_id": 0}) or {}
    return {**DEFAULT_SETTINGS, **doc}


# ---------- Catalog helpers ----------
def _catalog_router(name: str, collection: str):
    @router.get(f"/{name}")
    async def _list(user=Depends(get_current_user)):
        items = await db[collection].find({}, {"_id": 0}).sort("nombre", 1).to_list(5000)
        return items

    @router.post(f"/{name}")
    async def _create(payload: CatalogIn, user=Depends(require_roles("superadmin", "direccion"))):
        doc = {
            "id": str(uuid.uuid4()),
            "nombre": payload.nombre,
            "codigo": payload.codigo,
            "facultad_id": payload.facultad_id,
            "programa_id": payload.programa_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        await db[collection].insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.delete(f"/{name}/{{item_id}}")
    async def _delete(item_id: str, user=Depends(require_roles("superadmin", "direccion"))):
        await db[collection].delete_one({"id": item_id})
        return {"ok": True}

    return _list, _create, _delete


# Register catalog endpoints
_catalog_router("facultades", "facultades")
_catalog_router("programas", "programas")
_catalog_router("materias", "materias")
_catalog_router("periodos", "periodos")


# ---------- Docente-Materia ----------
@router.get("/docente-materia")
async def list_docente_materia(user=Depends(get_current_user)):
    items = await db.docente_materia.find({}, {"_id": 0}).to_list(5000)
    return items


@router.post("/docente-materia")
async def create_docente_materia(payload: DocenteMateriaIn, user=Depends(require_roles("superadmin", "direccion"))):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.utcnow().isoformat()
    await db.docente_materia.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.delete("/docente-materia/{item_id}")
async def delete_dm(item_id: str, user=Depends(require_roles("superadmin", "direccion"))):
    await db.docente_materia.delete_one({"id": item_id})
    return {"ok": True}



# ---------- Grupos (enriched with counts) ----------
@router.get("/grupos")
async def list_grupos(
    programa: str | None = None,
    facultad: str | None = None,
    periodo: str | None = None,
    docente_id: str | None = None,
    q: str | None = None,
    limit: int = 500,
    user=Depends(require_roles("superadmin", "direccion")),
):
    """Lista grupos enriquecidos con conteo de estudiantes matriculados y promedio del docente."""
    match = {}
    if programa: match["programa"] = programa
    if facultad: match["facultad"] = facultad
    if periodo: match["periodo"] = periodo
    if docente_id: match["docente_id"] = docente_id
    if q:
        rx = {"$regex": q, "$options": "i"}
        match["$or"] = [{"codigo_grupo": rx}, {"asignatura_nombre": rx}, {"docente_nombre": rx}, {"programa": rx}]

    grupos = await db.grupos.find(match, {"_id": 0}).sort("codigo_grupo", 1).limit(limit).to_list(limit)

    # Enrich with estudiantes count + promedio
    codigos = [g["codigo_grupo"] for g in grupos]
    if codigos:
        matr_pipe = [
            {"$match": {"codigo_grupo": {"$in": codigos}}},
            {"$group": {"_id": "$codigo_grupo", "n": {"$sum": 1}}},
        ]
        matr_map = {r["_id"]: r["n"] async for r in db.matriculas.aggregate(matr_pipe)}
        # Notes promedio (usando docente + asignatura para cruzar histórico)
        for g in grupos:
            g["total_estudiantes"] = matr_map.get(g["codigo_grupo"], 0)
            # Promedio: buscar notas por (docente_id + codigo_asignatura)
            if g.get("docente_id") and g.get("asignatura_codigo"):
                notas_agg = await db.historico_notas.aggregate([
                    {"$match": {"docente_id": g["docente_id"], "codigo_asignatura": g["asignatura_codigo"]}},
                    {"$group": {"_id": None, "prom": {"$avg": "$nota"}, "n": {"$sum": 1}}}
                ]).to_list(1)
                if notas_agg:
                    g["promedio_historico"] = round(notas_agg[0]["prom"] or 0, 2)
                    g["notas_historico"] = notas_agg[0]["n"]
                else:
                    g["promedio_historico"] = None
                    g["notas_historico"] = 0

    total = await db.grupos.count_documents(match)
    return {"items": grupos, "total": total, "limit": limit}


@router.get("/grupos/{codigo_grupo}")
async def get_grupo_detail(codigo_grupo: str, user=Depends(require_roles("superadmin", "direccion"))):
    """Detalle completo de un grupo: metadata + estudiantes + notas históricas."""
    grupo = await db.grupos.find_one({"codigo_grupo": codigo_grupo}, {"_id": 0})
    if not grupo:
        raise HTTPException(404, "Grupo no encontrado")

    # Matriculados
    matriculas = await db.matriculas.find(
        {"codigo_grupo": codigo_grupo},
        {"_id": 0, "cedula": 1, "estado": 1, "email_estudiante": 1, "email_institucional_estudiante": 1}
    ).to_list(500)
    cedulas = [m["cedula"] for m in matriculas]

    # Estudiantes enriquecidos
    estudiantes = []
    if cedulas:
        est_docs = await db.students.find(
            {"cedula": {"$in": cedulas}},
            {"_id": 0, "cedula": 1, "nombre": 1, "apellidos": 1, "programa": 1,
             "promedio": 1, "estrato": 1, "sisben_nivel": 1,
             "grupo_vulnerable": 1, "victima_conflicto": 1, "tipo_ubicacion": 1}
        ).to_list(500)
        est_map = {e["cedula"]: e for e in est_docs}
        for m in matriculas:
            e = est_map.get(m["cedula"], {})
            estudiantes.append({**e, "estado_matricula": m.get("estado")})

    # Notas históricas del docente en esa asignatura (todos los periodos)
    notas_periodos = []
    if grupo.get("docente_id") and grupo.get("asignatura_codigo"):
        pipe = [
            {"$match": {"docente_id": grupo["docente_id"], "codigo_asignatura": grupo["asignatura_codigo"]}},
            {"$group": {"_id": "$periodo", "prom": {"$avg": "$nota"}, "n": {"$sum": 1},
                        "aprob": {"$sum": {"$cond": ["$aprobada", 1, 0]}}}},
            {"$sort": {"_id": -1}},
            {"$project": {"_id": 0, "periodo": "$_id",
                          "promedio": {"$round": ["$prom", 2]}, "total": "$n",
                          "aprobadas": "$aprob",
                          "tasa": {"$round": [{"$multiply": [{"$divide": ["$aprob", "$n"]}, 100]}, 1]}}}
        ]
        notas_periodos = await db.historico_notas.aggregate(pipe).to_list(20)

    return {
        "grupo": grupo,
        "total_estudiantes": len(matriculas),
        "estudiantes": estudiantes,
        "notas_por_periodo": notas_periodos,
    }


# ---------- Facultades enriquecidas ----------
@router.get("/facultades-stats")
async def facultades_stats(user=Depends(require_roles("superadmin", "direccion"))):
    """Facultades con contadores de programas, estudiantes, docentes."""
    facs = await db.facultades.find({}, {"_id": 0}).to_list(50)
    for f in facs:
        f["total_programas"] = await db.programas.count_documents({"facultad_id": f["id"]})
        f["total_estudiantes"] = await db.students.count_documents({"facultad": f["nombre"]})
        f["total_grupos"] = await db.grupos.count_documents({"facultad": f["nombre"]})
        # Promedio
        prom_agg = await db.students.aggregate([
            {"$match": {"facultad": f["nombre"], "promedio": {"$gt": 0}}},
            {"$group": {"_id": None, "prom": {"$avg": "$promedio"}}}
        ]).to_list(1)
        f["promedio"] = round(prom_agg[0]["prom"], 2) if prom_agg else 0
    return facs


@router.put("/programas/{item_id}")
async def update_programa(item_id: str, payload: dict, user=Depends(require_roles("superadmin", "direccion"))):
    """Editar programa. Acepta campos parciales."""
    allowed = {"nombre", "nombre_corto", "codigo", "facultad_id", "facultad_nombre",
               "facultad_corta", "nivel", "modalidad", "estado"}
    upd = {k: v for k, v in payload.items() if k in allowed}
    if not upd:
        raise HTTPException(400, "Nada que actualizar")
    r = await db.programas.update_one({"id": item_id}, {"$set": upd})
    if not r.matched_count:
        raise HTTPException(404, "Programa no encontrado")
    return {"ok": True, "modified": r.modified_count}



# ---------- Docentes enriquecidos ----------
@router.get("/docentes")
async def list_docentes(user=Depends(require_roles("superadmin", "direccion"))):
    """Lista de docentes con datos completos + conteo de grupos/cursos/estudiantes."""
    docentes = await db.users.find(
        {"role": "profesor"},
        {"_id": 0, "password": 0}
    ).sort("full_name", 1).to_list(2000)

    # Precalcular grupos y estudiantes por docente_id
    grupos_by_doc = {}
    async for r in db.grupos.aggregate([
        {"$match": {"docente_id": {"$ne": None}}},
        {"$group": {
            "_id": "$docente_id",
            "n_grupos": {"$sum": 1},
            "materias": {"$addToSet": "$asignatura_nombre"},
            "programas": {"$addToSet": "$programa"},
            "periodos": {"$addToSet": "$periodo"},
        }}
    ]):
        grupos_by_doc[r["_id"]] = {
            "n_grupos": r["n_grupos"],
            "n_materias": len([m for m in r["materias"] if m]),
            "materias": sorted([m for m in r["materias"] if m])[:10],
            "programas": sorted([p for p in r["programas"] if p]),
            "periodos": sorted([p for p in r["periodos"] if p]),
        }

    # Estudiantes únicos por docente (via matriculas)
    estud_by_doc = {}
    async for r in db.matriculas.aggregate([
        {"$match": {"docente_id": {"$ne": None}}},
        {"$group": {"_id": "$docente_id", "cedulas": {"$addToSet": "$cedula"}}},
        {"$project": {"n": {"$size": "$cedulas"}}}
    ]):
        estud_by_doc[r["_id"]] = r["n"]

    for d in docentes:
        stats = grupos_by_doc.get(d["id"], {})
        d["n_grupos"] = stats.get("n_grupos", 0)
        d["n_materias"] = stats.get("n_materias", 0)
        d["materias"] = stats.get("materias", [])
        d["programas"] = stats.get("programas", [])
        d["periodos"] = stats.get("periodos", [])
        d["n_estudiantes"] = estud_by_doc.get(d["id"], 0)

    return docentes


@router.get("/docentes/{docente_id}/grupos")
async def docente_grupos(docente_id: str, user=Depends(require_roles("superadmin", "direccion"))):
    """Grupos asignados a un docente con conteo de estudiantes."""
    grupos = await db.grupos.find({"docente_id": docente_id}, {"_id": 0}).to_list(500)
    for g in grupos:
        g["n_estudiantes"] = await db.matriculas.count_documents({"codigo_grupo": g["codigo_grupo"]})
        # Notas históricas del docente en esa asignatura
        if g.get("asignatura_codigo"):
            agg = await db.historico_notas.aggregate([
                {"$match": {"docente_id": docente_id, "codigo_asignatura": g["asignatura_codigo"]}},
                {"$group": {"_id": "$periodo", "prom": {"$avg": "$nota"}, "n": {"$sum": 1}}},
                {"$sort": {"_id": -1}}
            ]).to_list(10)
            g["historico_notas"] = [{"periodo": a["_id"], "promedio": round(a["prom"] or 0, 2), "n": a["n"]} for a in agg]
        else:
            g["historico_notas"] = []
    return grupos
