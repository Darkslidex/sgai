"""
Script de verificación integral del sistema SGAI.
Comprueba que todos los componentes críticos funcionan correctamente.

Uso:
    python -m scripts.verify_system
"""

import asyncio
import os
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


async def _check_db_connection() -> Check:
    """Verifica que la base de datos está accesible."""
    try:
        from app.database import init_db, get_session
        from app.config import get_settings
        from sqlalchemy import text

        settings = get_settings()
        init_db(settings.database_url)
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        return Check("DB conectada", True, "Conexión exitosa")
    except Exception as e:
        return Check("DB conectada", False, str(e))


async def _check_tables_exist() -> Check:
    """Verifica que las 10 tablas del dominio existen."""
    expected_tables = {
        "user_profiles", "health_logs", "recipes", "recipe_ingredients",
        "ingredients", "market_prices", "pantry_items",
        "weekly_plans", "optimization_logs", "user_preferences",
    }
    try:
        from app.database import get_session
        from sqlalchemy import text

        async with get_session() as session:
            result = await session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            )
            existing = {row[0] for row in result.fetchall()}

        missing = expected_tables - existing
        if missing:
            return Check("Tablas (10)", False, f"Faltan: {', '.join(sorted(missing))}")
        return Check("Tablas (10)", True, f"{len(existing)} tablas encontradas")
    except Exception as e:
        return Check("Tablas (10)", False, str(e))


async def _check_seed_data() -> Check:
    """Verifica que hay ingredientes y recetas en la base de datos."""
    try:
        from app.database import get_session
        from sqlalchemy import text

        async with get_session() as session:
            r1 = await session.execute(text("SELECT COUNT(*) FROM ingredients"))
            r2 = await session.execute(text("SELECT COUNT(*) FROM recipes"))
            ing_count = r1.scalar()
            rec_count = r2.scalar()

        if ing_count < 60:
            return Check("Seed data", False, f"Solo {ing_count} ingredientes (esperados 60+)")
        if rec_count < 15:
            return Check("Seed data", False, f"Solo {rec_count} recetas (esperadas 15+)")
        return Check("Seed data", True, f"{ing_count} ingredientes, {rec_count} recetas")
    except Exception as e:
        return Check("Seed data", False, str(e))


async def _check_health_endpoint() -> Check:
    """Verifica que el endpoint /health responde."""
    try:
        import httpx
        from app.config import get_settings

        settings = get_settings()
        base_url = os.environ.get("APP_BASE_URL", "http://localhost:8000")
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base_url}/health")
        if resp.status_code == 200 and resp.json().get("status") == "ok":
            return Check("/health endpoint", True, f"status={resp.json()['status']}")
        return Check("/health endpoint", False, f"status_code={resp.status_code}")
    except Exception as e:
        return Check("/health endpoint", False, f"No responde: {e}")


async def _check_telegram_token() -> Check:
    """Verifica que el token de Telegram es válido (getMe)."""
    try:
        import httpx
        from app.config import get_settings

        settings = get_settings()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
            )
        data = resp.json()
        if data.get("ok"):
            bot_name = data["result"].get("username", "?")
            return Check("Telegram token", True, f"Bot: @{bot_name}")
        return Check("Telegram token", False, f"API respondió: {data.get('description', '?')}")
    except Exception as e:
        return Check("Telegram token", False, str(e))


async def _check_deepseek_api() -> Check:
    """Verifica que la API de DeepSeek responde (ping liviano con 1 token)."""
    try:
        import httpx
        from app.config import get_settings

        settings = get_settings()
        payload = {
            "model": settings.deepseek_model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "temperature": 0,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.deepseek_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json=payload,
            )
        if resp.status_code == 200:
            return Check("DeepSeek API", True, "Responde OK")
        return Check("DeepSeek API", False, f"HTTP {resp.status_code}")
    except Exception as e:
        return Check("DeepSeek API", False, str(e))


def _check_encryption() -> Check:
    """Verifica que el cifrado Fernet funciona (encrypt + decrypt roundtrip)."""
    try:
        from cryptography.fernet import Fernet
        from app.adapters.persistence.encryption import DataEncryptor

        key = Fernet.generate_key().decode()
        enc = DataEncryptor(key)
        original = "dato_sensible_42.5"
        assert enc.decrypt(enc.encrypt(original)) == original
        return Check("Cifrado Fernet", True, "Roundtrip encrypt/decrypt OK")
    except Exception as e:
        return Check("Cifrado Fernet", False, str(e))


def _check_no_secrets_in_code() -> Check:
    """Verifica que no hay API keys hardcodeadas en el código fuente."""
    try:
        result = subprocess.run(
            ["grep", "-r", "sk-", "app/", "--include=*.py", "-l"],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__))
        )
        files_with_keys = [f for f in result.stdout.strip().split("\n") if f]
        if files_with_keys:
            return Check("Sin secrets en código", False, f"Encontrado en: {files_with_keys}")
        return Check("Sin secrets en código", True, "Ningún sk-* hardcodeado")
    except Exception as e:
        return Check("Sin secrets en código", False, str(e))


def _check_tests_pass() -> Check:
    """Ejecuta el suite de tests y verifica que todos pasan."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no", "--no-header"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            # Extraer el resumen "X passed"
            summary = [l for l in output.split("\n") if "passed" in l]
            detail = summary[-1].strip() if summary else "Tests OK"
            return Check("Tests automatizados", True, detail)
        # Extraer líneas de error
        failed_lines = [l for l in output.split("\n") if "FAILED" in l or "ERROR" in l]
        return Check("Tests automatizados", False, "; ".join(failed_lines[:3]))
    except Exception as e:
        return Check("Tests automatizados", False, str(e))


async def verify() -> bool:
    """Ejecuta todas las verificaciones y muestra el resultado."""
    print("\n🔍 SGAI — Verificación Integral del Sistema\n" + "=" * 50)

    # Checks async
    async_checks = await asyncio.gather(
        _check_db_connection(),
        _check_tables_exist(),
        _check_seed_data(),
        _check_health_endpoint(),
        _check_telegram_token(),
        _check_deepseek_api(),
    )

    # Checks síncronos
    sync_checks = [
        _check_encryption(),
        _check_no_secrets_in_code(),
        _check_tests_pass(),
    ]

    all_checks: list[Check] = list(async_checks) + sync_checks

    passed = sum(1 for c in all_checks if c.passed)
    total = len(all_checks)

    for check in all_checks:
        icon = "✅" if check.passed else "❌"
        print(f"{icon} {check.name}: {check.detail}")

    print(f"\n{'=' * 50}")
    print(f"Resultado: {passed}/{total} verificaciones exitosas")

    if passed == total:
        print("🎉 Sistema listo para producción")
    else:
        failed = [c.name for c in all_checks if not c.passed]
        print(f"⚠️  Resolver antes del deploy: {', '.join(failed)}")

    return passed == total


if __name__ == "__main__":
    # Cargar .env si existe
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_file):
        from dotenv import load_dotenv
        load_dotenv(env_file)

    result = asyncio.run(verify())
    sys.exit(0 if result else 1)
