# SGAI — Sistema de Gestión Alimenticia Inteligente

Sistema personal de planificación nutricional con IA, bot de Telegram y dashboard web. Diseñado para uso single-user con arquitectura hexagonal, deploy en Railway y privacidad total de los datos.

## Descripción

SGAI no es una app de dietas convencional. Es una herramienta de gestión de recursos que usa análisis de datos, IA (DeepSeek) y telemetría biométrica para optimizar la adherencia al plan nutricional mediante:

- **Batch Cooking 1x5**: planificación semanal que minimiza tiempo de cocina
- **Precios híbridos**: datos reales de supermercados (manual → SEPA → scraping)
- **TDEE dinámico**: ajuste calórico por estrés, sueño y HRV (Harris-Benedict)
- **Anti-desperdicio (ADR-008)**: ratio consumo/vencimiento para evitar pérdidas
- **Mood & Food**: correlaciones entre bienestar y adherencia al plan

## Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│                     Interfaces de Usuario                 │
│   Bot Telegram (python-telegram-bot) │ Dashboard (Streamlit) │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP / session_state
┌────────────────────▼─────────────────────────────────────┐
│                    FastAPI (app/)                          │
│   /api/v1/ · /health · Middleware · APScheduler           │
└────────────────────┬─────────────────────────────────────┘
                     │ Ports (ABC)
┌────────────────────▼─────────────────────────────────────┐
│                  Dominio (Hexagonal)                       │
│  PlanningService · PriceService · HealthService            │
│  PantryService · ConsumptionRatioService · MoodFoodService │
└────────────────────┬─────────────────────────────────────┘
                     │ Adapters
┌────────────────────▼─────────────────────────────────────┐
│              Adapters de Infraestructura                   │
│  PostgreSQL (SQLAlchemy async) │ DeepSeek API              │
│  SEPA API │ Scraping (httpx)   │ Fernet (cifrado)          │
└──────────────────────────────────────────────────────────┘
```

## Requisitos

- Python 3.12+
- PostgreSQL 15+
- Cuenta Railway (para deploy)
- Token de bot de Telegram (`@BotFather`)
- API Key de DeepSeek

## Instalación Local

```bash
# 1. Clonar y crear entorno virtual
git clone <repo>
cd sgai
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 4. Correr migraciones
alembic upgrade head

# 5. Cargar datos de seed
python -m scripts.seed_all

# 6. Levantar el servidor
uvicorn app.main:app --reload

# 7. Dashboard (en otra terminal)
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Variables de Entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | URL async de PostgreSQL | `postgresql+asyncpg://user:pass@host/db` |
| `DEEPSEEK_API_KEY` | API Key de DeepSeek | `sk-...` |
| `DEEPSEEK_BASE_URL` | URL base de DeepSeek | `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | Modelo a usar | `deepseek-chat` |
| `TELEGRAM_BOT_TOKEN` | Token del bot | `123456:ABC...` |
| `TELEGRAM_ALLOWED_CHAT_IDS` | Chat IDs autorizados (CSV) | `6513721904` |
| `JWT_SECRET_KEY` | Clave para JWTs | `secreto-aleatorio-largo` |
| `ENCRYPTION_KEY` | Clave Fernet para datos sensibles (opcional) | ver abajo |
| `APP_ENV` | Entorno | `development` / `production` |
| `DASHBOARD_USER` | Usuario del dashboard web | `chef` |
| `DASHBOARD_PASSWORD_HASH` | Hash bcrypt de la contraseña | ver abajo |

**Generar ENCRYPTION_KEY:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Generar DASHBOARD_PASSWORD_HASH:**
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'tu_contraseña', bcrypt.gensalt()).decode())"
```

## Estructura del Proyecto

```
sgai/
├── app/
│   ├── domain/
│   │   ├── models/           # Dataclasses puras (sin ORM)
│   │   ├── ports/            # Interfaces abstractas (ABC)
│   │   └── services/         # Lógica de negocio
│   ├── adapters/
│   │   ├── ai/               # DeepSeek adapter + prompts
│   │   ├── health/           # Manual + HealthConnect adapters
│   │   ├── llm/              # Prompts Mood & Food
│   │   ├── persistence/      # SQLAlchemy repos + encryption
│   │   ├── pricing/          # Manual, SEPA, Scraping adapters
│   │   └── telegram/         # Bot, handlers, parsers, security
│   ├── api/
│   │   ├── v1/               # Endpoints CRUD
│   │   ├── middleware.py     # Logging + Rate limiting
│   │   └── error_handlers.py # Handlers globales
│   ├── config.py             # Pydantic Settings v2
│   ├── database.py           # SQLAlchemy async engine
│   └── main.py               # FastAPI app factory + lifespan
├── dashboard/
│   ├── app.py                # Entry point Streamlit
│   ├── auth.py               # bcrypt auth + sesiones
│   ├── config.py             # DashboardSettings
│   ├── components/           # API client, charts, styles
│   └── pages/                # 7 páginas (estética restaurante de lujo)
├── scripts/
│   ├── seed_all.py           # Seed completo (65 ingredientes, 16 recetas)
│   └── verify_system.py      # Verificación integral pre-deploy
├── tests/                    # 250+ tests automatizados
├── .pre-commit-config.yaml   # Detección de secrets
├── alembic.ini
├── railway.toml
└── requirements.txt
```

## Comandos del Bot de Telegram

| Comando | Descripción |
|---------|-------------|
| `/start` | Bienvenida y estado rápido |
| `/setup` | Crear/actualizar perfil (flujo conversacional 5 pasos) |
| `/perfil` | Ver perfil nutricional |
| `/estado` | Resumen general del sistema |
| `/salud sueno:7 estres:medio pasos:8000` | Registrar métricas de salud |
| `/tdee` | TDEE dinámico con ajuste por estrés/sueño |
| `/energia` | Estado energético (Normal / Baja Energía / Crítico) |
| `/plan` | Generar plan semanal Batch Cooking 1×5 con IA |
| `/mi_plan` | Ver lista de compras del plan activo |
| `/swap <ingrediente>` | Sustitutos por eficiencia nutricional |
| `/eficiencia` | Ranking ingredientes por costo/proteína (ADR-008) |
| `/precio <ingrediente> <precio>` | Registrar precio manual |
| `/precios` | Precios actuales del plan (fuente + confianza) |
| `/precio_detalle <ingrediente>` | Historial de precios últimos 30 días |
| `/pantry` | Ver alacena actual |
| `/agregar_pantry <ing> <cantidad> <unidad>` | Agregar al pantry |
| `/vencimientos` | Items próximos a vencer + riesgo ADR-008 |
| `/desperdicio` | Reporte completo anti-desperdicio |
| `/mood` | Correlaciones bienestar ↔ alimentación (requiere 4 semanas) |
| `/reporte` | Reporte semanal consolidado: salud + plan + insight |

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del sistema (uptime, DB, versión) |
| POST | `/api/v1/users/profile` | Crear perfil de usuario |
| GET/PUT | `/api/v1/users/profile/{id}` | Leer/actualizar perfil |
| POST | `/api/v1/health/logs` | Registrar log de salud diario |
| GET | `/api/v1/health/logs/{user_id}` | Historial de salud |
| GET | `/api/v1/health/tdee/{user_id}` | TDEE dinámico calculado |
| GET | `/api/v1/health/energy-state/{user_id}` | Estado energético actual |
| GET/POST | `/api/v1/ingredients/` | Catálogo de ingredientes |
| GET/POST | `/api/v1/market/prices` | Precios de mercado |
| GET/POST | `/api/v1/market/pantry` | Gestión del pantry |
| GET/POST | `/api/v1/recipes/` | Recetas batch cooking |

Rate limits: **60 req/min** (general), **10 req/hora** (IA: `/plan`, `/swap`).

## Desarrollo

```bash
# Correr todos los tests
pytest tests/ -v

# Tests por módulo
pytest tests/unit/test_prices/ -v
pytest tests/test_dashboard_auth.py -v
pytest tests/test_mood_food.py -v

# Verificación integral
python -m scripts.verify_system

# Linting y detección de secrets
pre-commit run --all-files
```

## Seguridad

- **Bot Telegram**: whitelist de `chat_id` — solo el usuario autorizado puede interactuar
- **Dashboard web**: bcrypt + rate limiting (5 intentos) + bloqueo 5 min + sesión 30 min
- **API**: rate limiting en memoria, validación estricta por Pydantic, sin SQL injection posible (SQLAlchemy parametrizado)
- **Cifrado**: Fernet opcional para datos sensibles (`ENCRYPTION_KEY`)
- **Error handling**: nunca se exponen stack traces ni detalles internos
- **Pre-commit hooks**: detección automática de API keys antes de cada commit
- **Logs**: nunca se loguean bodies (datos personales), solo método/path/status/ms

## Licencia

Uso personal. No distribuir sin autorización.
