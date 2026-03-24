#!/usr/bin/env bash
# backup_db.sh — Genera un dump comprimido de PostgreSQL con timestamp y retención 7 días.
#
# Uso manual:
#   bash scripts/backup_db.sh
#
# Automatización:
#   - Cron: 0 3 * * * /path/to/sgai/scripts/backup_db.sh
#   - APScheduler: llamar como subprocess desde Python.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
DUMP_FILE="${BACKUP_DIR}/sgai_${TIMESTAMP}.sql"
GZ_FILE="${DUMP_FILE}.gz"

# Crear directorio si no existe
mkdir -p "$BACKUP_DIR"

# DATABASE_URL esperada en formato: postgresql://user:pass@host:port/dbname
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL no está definida." >&2
    exit 1
fi

echo "[$(date -u '+%Y-%m-%d %H:%M:%S')] Iniciando backup: ${GZ_FILE}"

# Exportar password para pg_dump (evita prompt interactivo)
export PGPASSWORD
PGPASSWORD=$(python3 -c "from urllib.parse import urlparse; u=urlparse('${DATABASE_URL}'); print(u.password or '')" 2>/dev/null || echo "")

pg_dump --no-acl --no-owner "${DATABASE_URL}" -f "${DUMP_FILE}"

# Comprimir y eliminar el dump sin comprimir
gzip "${DUMP_FILE}"

echo "[$(date -u '+%Y-%m-%d %H:%M:%S')] Backup completado: ${GZ_FILE}"

# Retención: eliminar backups más viejos que RETENTION_DAYS días
find "${BACKUP_DIR}" -name "sgai_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete
echo "[$(date -u '+%Y-%m-%d %H:%M:%S')] Retención aplicada (>${RETENTION_DAYS} días eliminados)"
