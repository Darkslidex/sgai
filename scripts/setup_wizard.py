"""
Asistente de configuración inicial de SGAI.

Primera ejecución: configura el .env, crea las tablas, carga los datos
iniciales y registra el perfil del usuario.

Reejectable en cualquier momento — detecta qué ya está hecho y solo
completa lo que falta.

Uso:
    python -m scripts.setup_wizard
    # o simplemente:
    make setup
"""

import asyncio
import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"

# ─── Estilos de terminal ──────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
RED    = "\033[31m"
DIM    = "\033[2m"


def _c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"


def header(title: str) -> None:
    print(f"\n{BOLD}{CYAN}── {title} {'─' * max(0, 50 - len(title))}{RESET}")


def ok(msg: str) -> None:
    print(f"  {_c(GREEN, '✓')} {msg}")


def warn(msg: str) -> None:
    print(f"  {_c(YELLOW, '!')} {msg}")


def error(msg: str) -> None:
    print(f"  {_c(RED, '✗')} {msg}")


def info(msg: str) -> None:
    print(f"  {_c(DIM, '·')} {msg}")


# ─── Lectura / escritura de .env ─────────────────────────────────────────────

def load_env_file(path: Path) -> dict[str, str]:
    """Lee el .env actual y devuelve un dict {KEY: value}."""
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def write_env_file(path: Path, env: dict[str, str]) -> None:
    """Escribe el .env con secciones organizadas."""
    sections = [
        ("Base de Datos", ["DATABASE_URL"]),
        ("DeepSeek API", ["DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"]),
        ("Telegram Bot", ["TELEGRAM_BOT_ENABLED", "TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_CHAT_IDS"]),
        ("Integración Ana (OpenClaw)", ["ANA_API_KEY", "OPENCLAW_WEBHOOK_URL", "SGAI_OUTBOUND_KEY"]),
        ("Seguridad", ["JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_EXPIRATION_MINUTES"]),
        ("App", ["APP_ENV", "APP_DEBUG", "LOG_LEVEL"]),
    ]
    lines: list[str] = ["# SGAI — Configuración de entorno", "# Generado por setup_wizard.py", ""]
    written: set[str] = set()

    for section_name, keys in sections:
        section_lines = []
        for key in keys:
            if key in env:
                section_lines.append(f"{key}={env[key]}")
                written.add(key)
        if section_lines:
            lines.append(f"# === {section_name} ===")
            lines.extend(section_lines)
            lines.append("")

    # Claves extra no contempladas en las secciones
    extras = [f"{k}={v}" for k, v in env.items() if k not in written]
    if extras:
        lines.append("# === Otras ===")
        lines.extend(extras)
        lines.append("")

    path.write_text("\n".join(lines))


# ─── Helpers de entrada ───────────────────────────────────────────────────────

def ask(prompt: str, default: str | None = None, secret: bool = False) -> str:
    """Pide un valor al usuario. Si hay default, se muestra entre corchetes."""
    hint = f" [{_c(DIM, default)}]" if default else ""
    full_prompt = f"  {BOLD}{prompt}{RESET}{hint}: "
    while True:
        try:
            if secret:
                import getpass
                value = getpass.getpass(full_prompt)
            else:
                value = input(full_prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)
        if value:
            return value
        if default is not None:
            return default
        error("Este campo es requerido.")


def ask_yn(prompt: str, default: bool = True) -> bool:
    """Pregunta sí/no."""
    hint = "[S/n]" if default else "[s/N]"
    full_prompt = f"  {BOLD}{prompt}{RESET} {_c(DIM, hint)}: "
    try:
        value = input(full_prompt).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
    if not value:
        return default
    return value in ("s", "si", "sí", "y", "yes", "1")


def ask_choice(prompt: str, choices: list[tuple[str, str]], default_key: str | None = None) -> str:
    """Menú numerado. choices = [(key, label), ...]."""
    print(f"\n  {BOLD}{prompt}{RESET}")
    for i, (key, label) in enumerate(choices, 1):
        marker = _c(CYAN, "→") if key == default_key else " "
        print(f"  {marker} {i}. {label}")
    keys = [k for k, _ in choices]
    default_n = keys.index(default_key) + 1 if default_key in keys else None
    hint = f" [{default_n}]" if default_n else ""
    while True:
        try:
            raw = input(f"\n  Opción{hint}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)
        if not raw and default_n:
            return default_key  # type: ignore[return-value]
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx][0]
        error(f"Ingresá un número entre 1 y {len(choices)}.")


# ─── Test de conectividad a PostgreSQL ───────────────────────────────────────

async def test_db_connection(url: str) -> bool:
    """Intenta conectar a PostgreSQL. Devuelve True si tiene éxito."""
    try:
        import asyncpg  # type: ignore[import-untyped]
        # asyncpg usa su propio formato de URL (sin +asyncpg)
        pg_url = url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncio.wait_for(asyncpg.connect(pg_url), timeout=5)
        await conn.close()
        return True
    except Exception:
        return False


# ─── Sección: Base de datos ───────────────────────────────────────────────────

async def step_database(env: dict[str, str]) -> None:
    header("Base de Datos")

    default_url = env.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/sgai")

    while True:
        url = ask("DATABASE_URL", default=default_url)

        # Normalizar: si el usuario pega una URL sin +asyncpg, agregarla
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        info("Probando conexión...")
        if await test_db_connection(url):
            ok("Conexión exitosa.")
            env["DATABASE_URL"] = url
            return
        else:
            error("No se pudo conectar. Verificá que PostgreSQL esté corriendo y los datos sean correctos.")
            warn("Si no tenés PostgreSQL instalado:")
            info("  sudo apt install postgresql postgresql-contrib")
            info("  sudo service postgresql start")
            info("  sudo -u postgres psql -c \"CREATE DATABASE sgai;\"")
            if not ask_yn("¿Querés intentar con otra URL?"):
                error("No se puede continuar sin base de datos.")
                sys.exit(1)


# ─── Sección: DeepSeek ────────────────────────────────────────────────────────

def step_deepseek(env: dict[str, str]) -> None:
    header("DeepSeek API")
    info("Necesitás una API key de DeepSeek (platform.deepseek.com).")

    key = ask("DEEPSEEK_API_KEY", default=env.get("DEEPSEEK_API_KEY"), secret=True)
    env["DEEPSEEK_API_KEY"] = key
    env.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    env.setdefault("DEEPSEEK_MODEL", "deepseek-chat")
    ok("API key configurada.")


# ─── Sección: Seguridad ───────────────────────────────────────────────────────

def step_security(env: dict[str, str]) -> None:
    header("Seguridad")

    if not env.get("JWT_SECRET_KEY") or env.get("JWT_SECRET_KEY") == "generate-a-secure-random-key":
        jwt_key = secrets.token_hex(32)
        env["JWT_SECRET_KEY"] = jwt_key
        ok(f"JWT_SECRET_KEY generada automáticamente.")
    else:
        ok("JWT_SECRET_KEY ya configurada.")

    if not env.get("ANA_API_KEY") or env.get("ANA_API_KEY") == "generate-a-secure-random-key":
        env["ANA_API_KEY"] = secrets.token_hex(32)
        ok("ANA_API_KEY generada automáticamente.")

    if not env.get("SGAI_OUTBOUND_KEY") or env.get("SGAI_OUTBOUND_KEY") == "generate-a-secure-random-key":
        env["SGAI_OUTBOUND_KEY"] = secrets.token_hex(32)
        ok("SGAI_OUTBOUND_KEY generada automáticamente.")

    env.setdefault("JWT_ALGORITHM", "HS256")
    env.setdefault("JWT_EXPIRATION_MINUTES", "30")


# ─── Sección: Telegram ────────────────────────────────────────────────────────

def step_telegram(env: dict[str, str]) -> None:
    header("Telegram Bot")

    current_enabled = env.get("TELEGRAM_BOT_ENABLED", "true").lower() == "true"
    enabled = ask_yn("¿Activar el bot de Telegram?", default=current_enabled)
    env["TELEGRAM_BOT_ENABLED"] = "true" if enabled else "false"

    if not enabled:
        info("Bot desactivado. SGAI funcionará como API pura.")
        return

    info("Necesitás un bot de Telegram creado con @BotFather.")
    token = ask("TELEGRAM_BOT_TOKEN", default=env.get("TELEGRAM_BOT_TOKEN"), secret=True)
    env["TELEGRAM_BOT_TOKEN"] = token

    info("Tu chat ID lo podés conseguir hablándole a @userinfobot en Telegram.")
    chat_id = ask("Tu TELEGRAM_CHAT_ID (tu ID personal)", default=env.get("TELEGRAM_ALLOWED_CHAT_IDS"))
    env["TELEGRAM_ALLOWED_CHAT_IDS"] = chat_id
    ok("Bot de Telegram configurado.")


# ─── Sección: Ana (OpenClaw) ──────────────────────────────────────────────────

def step_ana(env: dict[str, str]) -> None:
    header("Integración con Ana (OpenClaw)")

    if ask_yn("¿Tenés Ana (OpenClaw) corriendo en el VPS?", default=bool(env.get("OPENCLAW_WEBHOOK_URL"))):
        url = ask("OPENCLAW_WEBHOOK_URL", default=env.get("OPENCLAW_WEBHOOK_URL", "http://localhost:18789/webhook"))
        env["OPENCLAW_WEBHOOK_URL"] = url
        ok("URL del gateway configurada.")
    else:
        env.pop("OPENCLAW_WEBHOOK_URL", None)
        info("Sin Ana configurada — las alertas irán directo a Telegram.")


# ─── Sección: App ─────────────────────────────────────────────────────────────

def step_app(env: dict[str, str]) -> None:
    header("Entorno de la app")
    env.setdefault("APP_ENV", "development")
    env.setdefault("APP_DEBUG", "false")
    env.setdefault("LOG_LEVEL", "INFO")


# ─── Migraciones y seed ───────────────────────────────────────────────────────

def run_cmd(cmd: list[str], desc: str) -> bool:
    """Ejecuta un subproceso. Devuelve True si tuvo éxito."""
    info(f"{desc}...")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode == 0:
        ok(f"{desc} — completado.")
        return True
    else:
        error(f"{desc} — falló.")
        print(_c(RED, result.stderr.strip()[-800:] if result.stderr else "(sin salida)"))
        return False


def step_migrations(env: dict[str, str]) -> bool:
    header("Migraciones de base de datos")
    env_with_db = {**os.environ, "DATABASE_URL": env["DATABASE_URL"]}
    info("Aplicando migraciones (alembic upgrade head)...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env_with_db,
    )
    if result.returncode == 0:
        ok("Tablas creadas / actualizadas.")
        return True
    error("Las migraciones fallaron.")
    print(_c(RED, result.stderr.strip()[-800:] if result.stderr else "(sin salida)"))
    return False


def step_seed(env: dict[str, str]) -> bool:
    header("Datos iniciales")
    env_with_db = {**os.environ, "DATABASE_URL": env["DATABASE_URL"]}
    info("Cargando ingredientes, precios de referencia y recetas...")
    result = subprocess.run(
        [sys.executable, "-m", "scripts.seed_all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env_with_db,
    )
    if result.returncode == 0:
        ok("Datos cargados correctamente.")
        return True
    error("El seed falló.")
    print(_c(RED, result.stderr.strip()[-800:] if result.stderr else "(sin salida)"))
    return False


# ─── Perfil de usuario ────────────────────────────────────────────────────────

async def _db_has_user(database_url: str) -> bool:
    """Devuelve True si ya existe al menos un usuario en la DB."""
    try:
        # Necesitamos importar los módulos de la app ahora que .env está escrito
        sys.path.insert(0, str(ROOT))
        os.environ["DATABASE_URL"] = database_url
        # Import tardío para que pick up el DATABASE_URL correcto
        from app.adapters.persistence.user_profile_orm import UserProfileORM  # noqa: F401
        from app.database import Base, get_session, init_db
        from sqlalchemy import select, text

        init_db(database_url)
        async with get_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM user_profiles"))
            count = result.scalar()
            return int(count) > 0
    except Exception:
        return False


async def _create_user_in_db(database_url: str, profile_data: dict) -> bool:
    """Inserta el perfil de usuario directamente en la DB."""
    try:
        from datetime import datetime

        from app.adapters.persistence.user_profile_orm import UserProfileORM
        from app.database import get_session, init_db

        init_db(database_url)
        async with get_session() as session:
            orm = UserProfileORM(
                telegram_chat_id=profile_data["telegram_chat_id"],
                name=profile_data["name"],
                age=profile_data["age"],
                weight_kg=profile_data["weight_kg"],
                height_cm=profile_data["height_cm"],
                activity_level=profile_data["activity_level"],
                goal=profile_data["goal"],
                max_storage_volume=profile_data.get("max_storage_volume", {}),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(orm)
            await session.commit()
        return True
    except Exception as exc:
        error(f"No se pudo crear el perfil: {exc}")
        return False


async def step_user_profile(env: dict[str, str]) -> None:
    header("Tu perfil de usuario")

    database_url = env["DATABASE_URL"]

    if await _db_has_user(database_url):
        ok("Ya existe un perfil de usuario. Saltando este paso.")
        info("Para actualizar tu perfil usá PUT /api/v1/users/profile/1.")
        return

    print(f"\n  {BOLD}SGAI necesita conocerte para calcular tus necesidades nutricionales.{RESET}")
    print(f"  {DIM}Podés cambiar estos datos después desde la API.{RESET}\n")

    name = ask("Tu nombre")

    telegram_chat_id = ask(
        "Tu Telegram Chat ID",
        default=env.get("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")[0].strip() or None,
    )

    age_str = ask("Edad (años)")
    while not age_str.isdigit() or not (18 <= int(age_str) <= 120):
        error("Ingresá una edad válida (18-120).")
        age_str = ask("Edad (años)")

    weight_str = ask("Peso actual (kg, ej: 78.5)")
    try:
        weight = float(weight_str.replace(",", "."))
    except ValueError:
        weight = 80.0
        warn(f"No se pudo leer el peso, usando {weight} kg por defecto.")

    height_str = ask("Altura (cm, ej: 175)")
    try:
        height = float(height_str.replace(",", "."))
    except ValueError:
        height = 175.0
        warn(f"No se pudo leer la altura, usando {height} cm por defecto.")

    activity_level = ask_choice(
        "Nivel de actividad física",
        [
            ("sedentary",  "Sedentario — trabajo de escritorio, casi sin ejercicio"),
            ("light",      "Ligero — 1-3 días de ejercicio a la semana"),
            ("moderate",   "Moderado — 3-5 días de ejercicio"),
            ("active",     "Activo — 6-7 días de ejercicio intenso"),
            ("very_active","Muy activo — trabajo físico + ejercicio diario"),
        ],
        default_key="moderate",
    )

    goal = ask_choice(
        "Objetivo nutricional",
        [
            ("maintain", "Mantener peso actual"),
            ("lose",     "Bajar de peso (déficit calórico moderado)"),
            ("gain",     "Ganar masa muscular (superávit calórico)"),
        ],
        default_key="maintain",
    )

    # Almacenamiento (opcional)
    max_storage: dict = {}
    if ask_yn("¿Querés configurar los límites de tu despensa? (podés hacerlo después)", default=False):
        print(f"  {DIM}Ingresá la capacidad aproximada en litros de cada espacio (Enter para saltar).{RESET}")
        for space, label in [("refrigerados", "Heladera"), ("secos", "Alacena / seco"), ("congelados", "Freezer")]:
            raw = ask(f"  {label} (litros)", default="").strip()
            if raw:
                try:
                    max_storage[space] = float(raw.replace(",", "."))
                except ValueError:
                    pass

    profile = {
        "telegram_chat_id": telegram_chat_id,
        "name": name,
        "age": int(age_str),
        "weight_kg": weight,
        "height_cm": height,
        "activity_level": activity_level,
        "goal": goal,
        "max_storage_volume": max_storage,
    }

    info("Guardando perfil...")
    if await _create_user_in_db(database_url, profile):
        ok(f"Perfil creado: {name}, {age_str} años, {weight} kg, {height} cm.")
    else:
        warn("No se pudo guardar el perfil automáticamente.")
        info("Podés crearlo después con: POST /api/v1/users/profile")


# ─── Resumen final ────────────────────────────────────────────────────────────

def print_summary(env: dict[str, str]) -> None:
    header("Configuración completada")
    print(f"""
  {BOLD}SGAI está listo para usar.{RESET}

  Para iniciar el servidor:
    {_c(CYAN, 'make start')}   o   {_c(CYAN, 'uvicorn app.main:app --reload')}

  API disponible en:
    {_c(CYAN, 'http://localhost:8000')}
    {_c(CYAN, 'http://localhost:8000/docs')}   ← Swagger UI

  Para verificar que todo funcione:
    {_c(CYAN, 'make verify')}

  Para ejecutar los tests:
    {_c(CYAN, 'make test')}

  {_c(DIM, f'ANA_API_KEY (para Ana/OpenClaw): {env.get("ANA_API_KEY", "—")}')}
""")


# ─── Detección de primer uso ──────────────────────────────────────────────────

def detect_state() -> tuple[bool, bool]:
    """Devuelve (env_exists, needs_full_setup)."""
    env_exists = ENV_FILE.exists()
    if not env_exists:
        return False, True
    env = load_env_file(ENV_FILE)
    # Si falta algún campo crítico, necesita setup completo
    missing = [k for k in ("DATABASE_URL", "DEEPSEEK_API_KEY", "JWT_SECRET_KEY") if not env.get(k)]
    return True, bool(missing)


# ─── Main ─────────────────────────────────────────────────────────────────────

async def _main() -> None:
    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════╗
║   SGAI — Sistema de Gestión Alimenticia Inteligente  ║
║                   Asistente de configuración         ║
╚══════════════════════════════════════════════════════╝{RESET}
""")

    env_exists, needs_full = detect_state()

    if env_exists and not needs_full:
        print(f"  {_c(GREEN, '✓')} Se encontró un .env existente.")
        if not ask_yn("¿Querés revisar / actualizar la configuración?", default=False):
            # Solo verificar si hay usuario y crearlo si falta
            env = load_env_file(ENV_FILE)
            await step_user_profile(env)
            print_summary(env)
            return

    if not env_exists:
        print(f"  {_c(YELLOW, '!')} No se encontró .env — iniciando configuración inicial.\n")

    # Cargar lo que haya actualmente como base de defaults
    env = load_env_file(ENV_FILE)

    # ── Pasos de configuración ────────────────────────────────────────────────
    await step_database(env)
    step_deepseek(env)
    step_security(env)
    step_telegram(env)
    step_ana(env)
    step_app(env)

    # ── Escribir .env ─────────────────────────────────────────────────────────
    header("Guardando configuración")
    write_env_file(ENV_FILE, env)
    ok(f".env guardado en {ENV_FILE}")

    # ── Migraciones ───────────────────────────────────────────────────────────
    if not step_migrations(env):
        warn("Podés intentar las migraciones manualmente con: make migrate")

    # ── Seed ──────────────────────────────────────────────────────────────────
    if not step_seed(env):
        warn("Podés cargar los datos manualmente con: make seed")

    # ── Perfil de usuario ─────────────────────────────────────────────────────
    await step_user_profile(env)

    # ── Resumen ───────────────────────────────────────────────────────────────
    print_summary(env)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
