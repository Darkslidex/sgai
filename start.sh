#!/bin/bash
set -e

echo "── SGAI startup ──────────────────────────"

echo "→ Aplicando migraciones..."
alembic upgrade head

echo "→ Cargando datos de seed..."
python -m scripts.seed_all

echo "→ Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
