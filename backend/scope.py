"""Role-based scope helpers.

Roles jerárquicos:
- superadmin, direccion: sin scope (ven todo)
- decano: filtra por facultad asignada (facultad_id → facultad_nombre)
- coordinador: filtra por programa asignado O por facultad si es coordinador de facultad
- profesor: filtra por estudiantes matriculados EN CUALQUIERA DE SUS GRUPOS (matriculas.docente_id == user.id)
"""
import re
from typing import Optional
from database import db


def _ci_regex(name: str) -> dict:
    """Case-insensitive exact match regex — la BD tiene mezclas de mayúsculas."""
    return {"$regex": f"^{re.escape(name)}$", "$options": "i"}


def apply_role_scope(user: dict, base_match: Optional[dict] = None) -> dict:
    """Devuelve un match filtrado por el scope del rol del usuario.

    Se debe aplicar sobre queries a `students` que tienen los campos
    string `facultad` y `programa`.

    Para `decano` sin facultad asignada o `coordinador` sin programa/facultad,
    devuelve un match imposible ({"_no_scope_": True}) para evitar fuga de datos.
    """
    m = dict(base_match or {})
    role = (user or {}).get("role")
    if role in ("superadmin", "direccion"):
        return m
    if role == "decano":
        fac = user.get("facultad_nombre")
        if not fac:
            m["_no_scope_"] = True  # ningún documento tiene este campo
        else:
            m["facultad"] = _ci_regex(fac)
        return m
    if role == "coordinador":
        prog = user.get("programa_nombre")
        fac = user.get("facultad_nombre")
        if prog:
            m["programa"] = _ci_regex(prog)
        elif fac:
            m["facultad"] = _ci_regex(fac)
        else:
            m["_no_scope_"] = True
        return m
    # profesor: usar apply_role_scope_async para recuperar cédulas
    return m


async def apply_role_scope_async(user: dict, base_match: Optional[dict] = None) -> dict:
    """Igual que `apply_role_scope` pero maneja profesor (async).

    Para role=profesor: filtra `students` a únicamente los estudiantes matriculados
    en cualquiera de los grupos del docente (matriculas.docente_id == user.id).
    Si el profesor no tiene ninguna matrícula, retorna un match imposible.
    """
    m = apply_role_scope(user, base_match)
    if (user or {}).get("role") != "profesor":
        return m

    # Recuperar cédulas de estudiantes matriculados en grupos de este docente.
    # `matriculas.docente_id` está denormalizado en la carga inicial.
    cedulas = await db.matriculas.distinct("cedula", {"docente_id": user["id"]})
    # También intentar por doc_estudiante (variante de esquema)
    if not cedulas:
        cedulas = await db.matriculas.distinct("doc_estudiante", {"docente_id": user["id"]})

    if not cedulas:
        # Docente sin estudiantes → resultado vacío garantizado.
        m["cedula"] = "__NO_MATCH__"
        return m

    # Si ya había un filtro por cedula, hacer intersección.
    existing = m.get("cedula")
    if isinstance(existing, dict) and "$in" in existing:
        merged = list(set(existing["$in"]) & set(cedulas))
        m["cedula"] = {"$in": merged} if merged else "__NO_MATCH__"
    else:
        m["cedula"] = {"$in": cedulas}
    return m


def get_role_scope_summary(user: dict) -> dict:
    """Devuelve un resumen legible del scope aplicado (para debug/UI)."""
    role = (user or {}).get("role")
    return {
        "role": role,
        "unrestricted": role in ("superadmin", "direccion"),
        "facultad_nombre": user.get("facultad_nombre") if role in ("decano", "coordinador") else None,
        "programa_nombre": user.get("programa_nombre") if role == "coordinador" else None,
        "missing_assignment": (
            (role == "decano" and not user.get("facultad_nombre")) or
            (role == "coordinador" and not user.get("programa_nombre") and not user.get("facultad_nombre"))
        ),
    }
