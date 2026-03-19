#!/usr/bin/env bash
# backup_db.sh — Genera un dump de la base de datos PostgreSQL con timestamp.
#
# Uso manual:
#   bash scripts/backup_db.sh
#
# Automatización:
#   - Cron: agregar a crontab -e, ej: 0 3 * * * /path/to/sgai/scripts/backup_db.sh
#   - APScheduler: llamar como subprocess desde Python en el scheduler de la app.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="${BACKUP_DIR}/sgai_${TIMESTAMP}.dump"

# Crear directorio si no existe
mkdir -p "$BACKUP_DIR"

# DATABASE_URL esperada en formato: postgresql://user:pass@host:port/dbname
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL no está definida." >&2
    exit 1
fi

echo "Iniciando backup: ${FILENAME}"
pg_dump --format=custom --no-acl --no-owner "${DATABASE_URL}" -f "${FILENAME}"
echo "Backup completado: ${FILENAME}"
