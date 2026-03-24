.PHONY: setup start test migrate seed verify help

VENV   := .venv/bin
PYTHON := $(VENV)/python3
APP    := app.main:app
PORT   := 8000

help:
	@echo ""
	@echo "  SGAI — Sistema de Gestión Alimenticia Inteligente"
	@echo ""
	@echo "  make setup    — Configuración inicial (primera vez)"
	@echo "  make start    — Iniciar el servidor en localhost:$(PORT)"
	@echo "  make test     — Ejecutar tests"
	@echo "  make migrate  — Aplicar migraciones pendientes"
	@echo "  make seed     — Cargar datos iniciales"
	@echo "  make verify   — Verificar el sistema completo"
	@echo ""

setup:
	$(PYTHON) -m scripts.setup_wizard


start:
	@if [ ! -f .env ]; then \
		echo ""; \
		echo "  ⚠️  No se encontró .env"; \
		echo "  Ejecutá 'make setup' para la configuración inicial."; \
		echo ""; \
		exit 1; \
	fi
	$(VENV)/uvicorn $(APP) --host 0.0.0.0 --port $(PORT) --reload

test:
	$(VENV)/pytest tests/ -v

migrate:
	$(VENV)/alembic upgrade head

seed:
	$(PYTHON) -m scripts.seed_all


verify:
	$(PYTHON) -m scripts.verify_system

