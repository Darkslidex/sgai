"""
Backup automatizado de la base de datos PostgreSQL.

Se ejecuta diariamente a las 03:00 UTC via APScheduler.
Guarda el dump localmente (advertencia: se pierde en redeploy de Railway).
TODO futuro: subir a Google Drive API o Cloudflare R2.
"""

import gzip
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("backups")
RETENTION_DAYS = 7


def _parse_db_url(database_url: str) -> dict:
    """Extrae componentes de la DATABASE_URL sin exponer secrets en logs."""
    parsed = urlparse(database_url)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "",
        "password": parsed.password or "",
        "dbname": (parsed.path or "/sgai").lstrip("/"),
    }


def run_backup(database_url: str | None = None) -> Path | None:
    """
    Ejecuta pg_dump y comprime con gzip.

    Args:
        database_url: URL de la DB. Si None, usa la variable de entorno DATABASE_URL.

    Returns:
        Path al archivo .sql.gz generado, o None si falló.
    """
    url = database_url or os.environ.get("DATABASE_URL", "")
    if not url:
        logger.error("Backup abortado: DATABASE_URL no definida")
        return None

    parts = _parse_db_url(url)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    dump_path = BACKUP_DIR / f"sgai_{timestamp}.sql"
    gz_path = Path(str(dump_path) + ".gz")

    env = os.environ.copy()
    env["PGPASSWORD"] = parts["password"]

    cmd = [
        "pg_dump",
        "-h", parts["host"],
        "-p", parts["port"],
        "-U", parts["user"],
        "-d", parts["dbname"],
        "--no-acl",
        "--no-owner",
        "-f", str(dump_path),
    ]

    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        logger.error("pg_dump falló: %s", exc.stderr.decode(errors="replace"))
        return None
    except FileNotFoundError:
        logger.error("pg_dump no está instalado — backup no disponible")
        return None

    # Comprimir con gzip
    with open(dump_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    dump_path.unlink()

    logger.info("Backup completado: %s", gz_path.name)
    return gz_path


def cleanup_old_backups(retention_days: int = RETENTION_DAYS) -> int:
    """Elimina backups con más de `retention_days` días. Retorna cantidad eliminada."""
    if not BACKUP_DIR.exists():
        return 0

    cutoff = datetime.now(timezone.utc).timestamp() - retention_days * 86400
    removed = 0
    for f in BACKUP_DIR.glob("sgai_*.sql.gz"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
            logger.info("Backup antiguo eliminado: %s", f.name)

    return removed


async def scheduled_backup() -> None:
    """Job de APScheduler: backup + limpieza de retención."""
    from app.config import get_settings

    settings = get_settings()
    result = run_backup(settings.database_url)
    if result:
        cleanup_old_backups()
    else:
        logger.warning("Backup diario falló — revisar configuración")
