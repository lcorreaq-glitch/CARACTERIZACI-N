#!/usr/bin/env bash
# =============================================================================
# Export MongoDB (ambiente actual Emergent) → dump BSON local
# =============================================================================
# Uso:
#   ./scripts/export_mongodb.sh [output_dir]
#
# Requiere: mongodump instalado localmente y acceso a MONGO_URL/DB_NAME.
# Genera un directorio con la copia binaria (rápido, preserva tipos BSON).
# =============================================================================
set -euo pipefail

OUT_DIR="${1:-./backup_$(date +%Y%m%d_%H%M%S)}"

# Cargar credenciales del backend/.env
if [ -f "./backend/.env" ]; then
  set -a; source ./backend/.env; set +a
fi

: "${MONGO_URL:?MONGO_URL no definida}"
: "${DB_NAME:?DB_NAME no definida}"

echo "→ Exportando '$DB_NAME' desde $MONGO_URL a $OUT_DIR"
mkdir -p "$OUT_DIR"

mongodump \
  --uri="$MONGO_URL" \
  --db="$DB_NAME" \
  --out="$OUT_DIR" \
  --gzip

echo "✓ Backup completado en: $OUT_DIR"
echo "  Colecciones exportadas:"
ls -lh "$OUT_DIR/$DB_NAME" 2>/dev/null | tail -n +2 | awk '{print "    -", $NF, "("$5")"}'
