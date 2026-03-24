"""Tests del sistema de backup (mocks de subprocess y filesystem)."""

import gzip
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.backup import cleanup_old_backups, run_backup


# ─────────────────────────────────────────────────────────────────────────────


def test_backup_generates_gz_file(tmp_path: Path) -> None:
    """run_backup genera un archivo .sql.gz con timestamp cuando pg_dump tiene éxito."""
    db_url = "postgresql://user:pass@localhost:5432/sgai"

    # Mock subprocess.run (simula pg_dump exitoso creando el dump file)
    def fake_run(cmd, env, check, capture_output):
        # El comando incluye -f <dump_path>; creamos el archivo
        dash_f_idx = cmd.index("-f")
        dump_file = Path(cmd[dash_f_idx + 1])
        dump_file.write_text("-- fake dump\n")
        return MagicMock(returncode=0)

    with (
        patch("app.adapters.backup.BACKUP_DIR", tmp_path),
        patch("subprocess.run", side_effect=fake_run),
    ):
        result = run_backup(db_url)

    assert result is not None
    assert result.suffix == ".gz"
    assert result.exists()
    # Verificar que el contenido es gzip válido
    with gzip.open(result, "rb") as f:
        content = f.read()
    assert b"fake dump" in content


def test_backup_returns_none_on_pg_dump_failure(tmp_path: Path) -> None:
    """run_backup retorna None cuando pg_dump falla."""
    import subprocess

    with (
        patch("app.adapters.backup.BACKUP_DIR", tmp_path),
        patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "pg_dump", stderr=b"error"),
        ),
    ):
        result = run_backup("postgresql://u:p@h/db")

    assert result is None


def test_backup_returns_none_without_database_url(tmp_path: Path) -> None:
    """run_backup retorna None si no hay DATABASE_URL."""
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    with (
        patch("app.adapters.backup.BACKUP_DIR", tmp_path),
        patch.dict(os.environ, env, clear=True),
    ):
        result = run_backup(None)

    assert result is None


def test_cleanup_removes_old_backups(tmp_path: Path) -> None:
    """cleanup_old_backups elimina archivos con más de 7 días."""
    old_file = tmp_path / "sgai_2020-01-01_00-00.sql.gz"
    old_file.write_bytes(b"old")
    # Forzar mtime en el pasado (más de 7 días)
    old_time = time.time() - 8 * 86400
    os.utime(old_file, (old_time, old_time))

    recent_file = tmp_path / "sgai_2099-01-01_00-00.sql.gz"
    recent_file.write_bytes(b"new")

    with patch("app.adapters.backup.BACKUP_DIR", tmp_path):
        removed = cleanup_old_backups(retention_days=7)

    assert removed == 1
    assert not old_file.exists()
    assert recent_file.exists()
