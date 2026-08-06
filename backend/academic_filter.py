"""Helper para filtrar notas académicas regulares (excluir extensión + inglés fuera de malla).

Usado en TODOS los tableros donde se calculan promedios/notas.
"""


# Regex de programas NO académicos (extensión, cursos, diplomados, inglés fuera de la malla)
NON_ACADEMIC_PROGRAM_REGEX = r"(extensi[oó]n\s+acad[eé]mica|^curso\s|diplomad|fuera\s+de\s+la\s+malla|-\s+extens)"


def academic_notes_match(base_match: dict = None) -> dict:
    """Devuelve un match de MongoDB que EXCLUYE notas de:
      - Cursos de Extensión Académica (codigo_asignatura empieza con 'EXT')
      - Cursos, Diplomados y ofertas fuera de malla (programa contiene esos patrones)
      - Inglés Fuera de la Malla (programa contiene 'fuera de la malla')

    Se combina con el `base_match` si se proporciona.
    """
    m = dict(base_match or {})
    # Combinar con $and para no pisar $or/$nor previos
    academic_conditions = [
        {"codigo_asignatura": {"$not": {"$regex": r"^EXT", "$options": "i"}}},
        {"$or": [
            {"programa": {"$exists": False}},
            {"programa": None},
            {"programa": ""},
            {"programa": {"$not": {"$regex": NON_ACADEMIC_PROGRAM_REGEX, "$options": "i"}}},
        ]},
    ]
    if "$and" in m:
        m["$and"] = list(m["$and"]) + academic_conditions
    else:
        m["$and"] = academic_conditions
    return m


def is_academic_note(note: dict) -> bool:
    """Version síncrona para chequear una nota individual."""
    import re
    cod = (note or {}).get("codigo_asignatura", "") or ""
    prog = (note or {}).get("programa", "") or ""
    if cod.upper().startswith("EXT"):
        return False
    if re.search(NON_ACADEMIC_PROGRAM_REGEX, prog, re.IGNORECASE):
        return False
    return True
