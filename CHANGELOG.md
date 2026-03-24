# Changelog — SGAI

Todos los cambios notables del proyecto se documentan en este archivo.
Formato basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0-mvp] — 2026-03-20

### Fase 4B — Seguridad, Dashboard final y Mood & Food

#### Agregado
- **`MoodFoodService`**: correlaciones Pearson entre 6 pares (sueño↔costo, estrés↔costo, HRV↔costo, pasos↔costo, sueño↔estrés, HRV↔sueño). Requiere 4+ semanas de datos. Insights generados por LLM con caché de 7 días
- **`DataEncryptor`** (`app/adapters/persistence/encryption.py`): cifrado simétrico Fernet (AES-128-CBC). `encrypt/decrypt` para strings, `encrypt_float/decrypt_float` para datos numéricos. Activado opcionalmente via `ENCRYPTION_KEY`
- **`RateLimitMiddleware`** (`app/api/middleware.py`): rate limiting en memoria. 10 req/hora para endpoints de IA (`/plan`, `/swap`), 60 req/min para el resto. Respuesta 429 con header `Retry-After`
- **`register_error_handlers`** (`app/api/error_handlers.py`): handlers globales para errores 500/404/429/422. Nunca expone stack traces. Mensajes en español
- **`generate_text`** en `DeepSeekAdapter`: método para generación de texto libre (sin JSON schema forzado), usado por MoodFoodService
- **Comandos Telegram** `/mood` y `/reporte`: correlaciones biometricas y reporte semanal consolidado (salud + plan + top insight)
- **Pre-commit hooks** (`.pre-commit-config.yaml`): `detect-private-key`, `check-added-large-files`, `check-merge-conflict`, `trailing-whitespace`, `end-of-file-fixer`, `detect-secrets` (Yelp)
- **`verify_system.py`** (`scripts/`): verificación integral pre-deploy con 9 checks async/sync (DB, tablas, seed data, /health, Telegram token, DeepSeek API, Fernet roundtrip, no hardcoded secrets, pytest suite)
- **Tests nuevos**: `test_mood_food.py` (9 tests), `test_encryption.py` (4 tests), `test_rate_limiting.py` (3 tests), `test_integration.py` (3 end-to-end)
- **`ENCRYPTION_KEY`** añadida a `app/config.py` como campo opcional Pydantic
- **`MOOD_FOOD_SYSTEM` prompt** (`app/adapters/llm/prompts/mood_food_prompt.py`)

#### Modificado
- `app/main.py`: agrega `RateLimitMiddleware` y `register_error_handlers`
- `app/adapters/telegram/bot.py`: registra handlers `/mood` y `/reporte`, actualiza `/ayuda`

---

## [0.9.0] — 2026-03-18

### Fase 4A — Dashboard Streamlit

#### Agregado
- **Dashboard web Streamlit** (`dashboard/`): 7 páginas con estética de restaurante de lujo (sidebar oscuro, cards Tailwind-style)
  - `01_overview.py` — Estado general del sistema
  - `02_salud.py` — Gráficos de salud (sleep, stress, HRV, pasos)
  - `03_plan.py` — Plan semanal activo + lista de compras
  - `04_precios.py` — Evolución de precios + análisis de mercado
  - `05_pantry.py` — Inventario con indicadores de vencimiento
  - `06_recetas.py` — Catálogo de recetas batch cooking
  - `07_mood_food.py` — Visualización correlaciones Mood & Food
- **`dashboard/auth.py`**: autenticación bcrypt + sesiones en memoria + rate limiting (5 intentos, bloqueo 5 min) + timeout de sesión 30 min
- **`dashboard/components/api_client.py`** (`SGAIClient`): cliente HTTP httpx sync con retry automático y manejo de errores
- **`dashboard/components/charts.py`**: helpers para gráficos Plotly (líneas, barras, radar)
- **`dashboard/components/styles.py`**: CSS custom inyectado vía `st.markdown`
- **`dashboard/config.py`** (`DashboardSettings`): variables de entorno del dashboard
- **`tests/test_dashboard_auth.py`**: 8 tests de autenticación (bcrypt, sesiones, rate limit, logout)
- **`tests/test_api_client.py`**: 6 tests del cliente HTTP del dashboard

#### Corregido
- Bug `st` variable collision en `05_pantry.py`: variable local `st` sobrescribía el import de streamlit en la sección "Por Almacenamiento"

---

## [0.8.0] — 2026-03-15

### Fase 3B — Módulos Pantry, Recetas y Anti-desperdicio

#### Agregado
- **`PantryService`**: gestión del inventario del usuario, alertas de vencimiento
- **`ConsumptionRatioService`** (ADR-008): ratio consumo/vencimiento por ingrediente, ranking de eficiencia por costo/proteína
- **Endpoints pantry** (`/api/v1/market/pantry`): CRUD completo de ítems del inventario
- **Comandos Telegram**: `/pantry`, `/agregar_pantry`, `/vencimientos`, `/desperdicio`, `/eficiencia`
- **Seeds completos** (`scripts/seed_all.py`): 65 ingredientes, 16 recetas batch cooking con macros y costos
- **Tablas ORM**: `pantry_items`, `optimization_logs`
- Tests unitarios para `PantryService` y `ConsumptionRatioService`

---

## [0.7.0] — 2026-03-12

### Fase 3A — Módulos de Precios y Mercado

#### Agregado
- **`PriceService`**: integración multi-fuente de precios (manual > SEPA > scraping) con factor de confianza
- **`SEPAAdapter`**: consulta a la API pública de precios SEPA del gobierno argentino
- **`ScrapingAdapter`**: scraping liviano con httpx + BeautifulSoup como fallback
- **Endpoints mercado** (`/api/v1/market/prices`): registrar y consultar precios con fuente y confianza
- **Comandos Telegram**: `/precio`, `/precios`, `/precio_detalle`, `/swap`
- **Tabla ORM**: `market_prices`
- Tests unitarios para `PriceService` con mocks de adapters

---

## [0.6.0] — 2026-03-08

### Fase 2B — Planificación Semanal con IA

#### Agregado
- **`PlanningService`**: generación de plan Batch Cooking 1×5 con DeepSeek. Considera TDEE, ingredientes disponibles, precios, anti-duplicados
- **`DeepSeekAdapter`** (`app/adapters/ai/`): cliente HTTP para DeepSeek API con retry, timeout configurable, JSON schema enforcement para respuestas
- **Prompt engineering** (`app/adapters/ai/prompts/`): prompts estructurados para plan semanal y sustitutos
- **Endpoints plan** (`/api/v1/plan`): generar plan, consultar plan activo
- **Comandos Telegram**: `/plan`, `/mi_plan`
- **Tablas ORM**: `weekly_plans`, `recipes`, `recipe_ingredients`
- Tests unitarios para `PlanningService` con `AsyncMock`

---

## [0.5.0] — 2026-03-04

### Fase 2A — Módulo de Salud y TDEE

#### Agregado
- **`HealthService`**: registro de métricas diarias (sueño, estrés, HRV, pasos, mood), cálculo de TDEE dinámico (Harris-Benedict + ajuste biométrico)
- **`HealthConnectAdapter`**: adapter para datos de wearables vía HealthConnect API
- **`ManualHealthAdapter`**: ingreso manual desde Telegram
- **Estado energético**: categorización Normal / Baja Energía / Crítico basada en sleep + HRV + estrés
- **Endpoints salud** (`/api/v1/health/`): log diario, TDEE, historial, estado energético
- **Comandos Telegram**: `/salud`, `/tdee`, `/energia`
- **Tablas ORM**: `health_logs`, `user_preferences`
- Tests unitarios para `HealthService`

---

## [0.4.0] — 2026-02-28

### Fase 1B — Bot Telegram MVP

#### Agregado
- **Bot Telegram** (`app/adapters/telegram/`): integración con python-telegram-bot
- **Security middleware bot**: whitelist de `chat_id`, rechazo de IDs no autorizados
- **Conversation handler**: flujo de 5 pasos para `/setup` (nombre, edad, peso, altura, objetivo)
- **Comandos básicos**: `/start`, `/setup`, `/perfil`, `/estado`, `/ayuda`
- **`TelegramParser`**: extracción de parámetros de mensajes texto (sin slash commands estructurados)
- Tests unitarios para security middleware y parser

---

## [0.3.0] — 2026-02-24

### Fase 1A — API REST y Perfil de Usuario

#### Agregado
- **FastAPI app** (`app/main.py`): factory pattern con lifespan, CORS, middleware de logging
- **Endpoints perfil** (`/api/v1/users/`): crear y consultar perfil de usuario con validación Pydantic
- **`RequestLoggingMiddleware`**: logging de método/path/status/ms sin loguear bodies
- **`/health` endpoint**: uptime, conexión DB, versión
- **`app/config.py`**: Pydantic Settings v2 con validación de variables de entorno
- **`app/database.py`**: SQLAlchemy async engine con `get_session` context manager
- **Modelos ORM**: `user_profiles`, `ingredients`
- Tests unitarios para endpoints (pytest + httpx AsyncClient)
- `conftest.py` con fixture `client` usando SQLite in-memory para tests

---

## [0.2.0] — 2026-02-20

### Arquitectura Hexagonal Base

#### Agregado
- Estructura de carpetas hexagonal: `domain/`, `adapters/`, `ports/`
- **Modelos de dominio** (dataclasses puras, sin ORM): `UserProfile`, `HealthLog`, `WeeklyPlan`, `Ingredient`, `MarketPrice`, `PantryItem`, `Recipe`
- **Puertos abstractos** (ABC): `UserRepositoryPort`, `HealthRepositoryPort`, `AIPlannerPort`, `PriceRepositoryPort`, `PantryRepositoryPort`, `RecipeRepositoryPort`
- Migraciones Alembic (`alembic/`)
- `requirements.txt` con dependencias pinadas
- `.env.example` con todas las variables documentadas
- `railway.toml` para deploy en Railway

---

## [0.1.0] — 2026-02-15

### Inicio del Proyecto

#### Agregado
- Repositorio inicializado
- Decisiones de arquitectura documentadas (ADR-001 a ADR-010):
  - ADR-001: Hexagonal Architecture
  - ADR-002: FastAPI + SQLAlchemy async
  - ADR-003: DeepSeek como LLM (costo/calidad)
  - ADR-004: PostgreSQL en Railway
  - ADR-005: python-telegram-bot
  - ADR-006: Streamlit para dashboard
  - ADR-007: Pydantic Settings v2
  - ADR-008: Anti-desperdicio ratio consumo/vencimiento
  - ADR-009: Precios multi-fuente con factor de confianza
  - ADR-010: Cifrado Fernet opt-in para datos sensibles
- README inicial
- `.gitignore` configurado
