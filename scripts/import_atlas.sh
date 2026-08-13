#!/usr/bin/env bash
# =============================================================================
# Import MongoDB dump → Google Cloud (MongoDB Atlas)
# =============================================================================
# Uso:
#   ./scripts/import_atlas.sh <dump_dir> <atlas_connection_string> <target_db_name>
#
# Ej:
#   ./scripts/import_atlas.sh ./backup_20260215_120000 \
#     "mongodb+srv://user:pass@iudigital.abcde.mongodb.net" \
#     iudigital_analitica_prod
# =============================================================================
set -euo pipefail

DUMP_DIR="${1:?Falta directorio de dump}"
ATLAS_URI="${2:?Falta connection string de Atlas}"
TARGET_DB="${3:?Falta target_db_name}"

# El dump está bajo <DUMP_DIR>/<origin_db_name>. Detectar el nombre.
ORIGIN_DB="$(ls "$DUMP_DIR" | head -n1)"
echo "→ Importando '$DUMP_DIR/$ORIGIN_DB' hacia Atlas DB '$TARGET_DB'"

mongorestore \
  --uri="$ATLAS_URI" \
  --nsFrom="${ORIGIN_DB}.*" \
  --nsTo="${TARGET_DB}.*" \
  --gzip \
  --dir="$DUMP_DIR" \
  --drop  # (opcional) elimina colecciones antes de importar. Quita si NO quieres reset

echo "✓ Restore completado en Atlas → $TARGET_DB"
echo "→ Verifique colecciones ejecutando en mongosh:"
echo "    use $TARGET_DB; db.getCollectionNames()"
