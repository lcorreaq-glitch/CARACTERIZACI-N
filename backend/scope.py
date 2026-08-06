"""Role-based scope helpers.

Roles jerárquicos:
- superadmin, direccion: sin scope (ven todo)
- decano: filtra por facultad asignada (facultad_id → facultad_nombre)
- coordinador: filtra por programa asignado O por facultad si es coordinador de facultad
- profesor: filtra por sus grupos (manejado en otras funciones — no acá)
"""
import re
from typing import Optional


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
    # profesor u otro: no aplicamos scope aquí (docente_router se encarga)
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
