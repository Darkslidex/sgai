# SGAI — Sistema de Gestión Alimenticia Inteligente

Sistema personal de gestión alimentaria con IA, construido con FastAPI, PostgreSQL y DeepSeek.

## Stack
- **Backend:** FastAPI + SQLAlchemy async + PostgreSQL
- **IA:** DeepSeek API
- **Bot:** Telegram
- **Deploy:** Railway
- **Arquitectura:** Hexagonal (ports & adapters)

## Setup local

```bash
cp .env.example .env
# Editar .env con tus valores
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Tests

```bash
pytest tests/ -v
```

## Migraciones

```bash
alembic upgrade head
alembic revision --autogenerate -m "descripcion"
```
