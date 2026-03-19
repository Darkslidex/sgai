"""
Bot de Telegram principal del SGAI.
Maneja comandos de texto. Todos los handlers están protegidos por authorized_only.
"""

import logging
from datetime import date, datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.adapters.persistence.health_repo import HealthRepository
from app.adapters.persistence.ingredient_repo import IngredientRepository
from app.adapters.persistence.market_repo import MarketRepository
from app.adapters.persistence.planning_repo import PlanningRepository
from app.adapters.persistence.user_repo import UserRepository
from app.adapters.telegram.audit import log_interaction
from app.adapters.telegram.conversations.setup import build_setup_handler
from app.adapters.telegram.parsers import parse_health_input, parse_pantry_input, parse_price_input
from app.adapters.telegram.security import authorized_only
from app.database import get_session
from app.domain.models.health import HealthLog
from app.domain.models.market import MarketPrice
from app.domain.models.pantry_item import PantryItem

logger = logging.getLogger(__name__)

# Multiplicadores de nivel de actividad → stress float
_STRESS_FLOAT = {"low": 2.0, "medium": 5.0, "high": 8.0, "critical": 10.0}

# Multiplicadores TDEE por nivel de actividad
_ACTIVITY_TDEE = {
    "sedentary": 1.2, "light": 1.375, "moderate": 1.55,
    "active": 1.725, "very_active": 1.9,
}


def _format_ars(amount: float) -> str:
    """Formatea un número como precio ARS con separador de miles: $1.500"""
    return f"${amount:,.0f}".replace(",", ".")


def _estimate_tdee(weight_kg: float, height_cm: float, age: int, activity_level: str) -> int:
    """Calcula TDEE usando BMR Mifflin-St Jeor (asume hombre por defecto)."""
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    multiplier = _ACTIVITY_TDEE.get(activity_level, 1.55)
    return int(bmr * multiplier)


# ─────────────────────────────────────────────────────────────── /start ──────

@authorized_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bienvenida. Si no hay perfil, invita a /setup."""

    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        repo = UserRepository(session)
        profile = await repo.get_profile_by_chat_id(chat_id)

    if profile is None:
        await update.message.reply_text(
            "👋 ¡Bienvenido a *SGAI* — Sistema de Gestión Alimenticia Inteligente!\n\n"
            "No tenés perfil configurado todavía.\n"
            "Usá /setup para crear tu perfil y comenzar.\n\n"
            "📋 Comandos disponibles: /ayuda",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"👋 ¡Hola de nuevo, *{profile.name}*!\n\n"
            f"⚖️ Peso: {profile.weight_kg} kg  |  🎯 Objetivo: {profile.goal}\n"
            "Usá /estado para ver el resumen completo.",
            parse_mode="Markdown",
        )
    await log_interaction(int(chat_id), "/start", True)


# ────────────────────────────────────────────────────────────── /perfil ──────

@authorized_only
async def cmd_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el perfil actual del usuario."""

    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        repo = UserRepository(session)
        profile = await repo.get_profile_by_chat_id(chat_id)

    if profile is None:
        await update.message.reply_text(
            "❌ No tenés perfil configurado.\nUsá /setup para crear uno."
        )
        return

    tdee = _estimate_tdee(profile.weight_kg, profile.height_cm, profile.age, profile.activity_level)
    await update.message.reply_text(
        f"👤 *Tu perfil*\n\n"
        f"Nombre: {profile.name}\n"
        f"Edad: {profile.age} años\n"
        f"Peso: {profile.weight_kg} kg\n"
        f"Altura: {profile.height_cm} cm\n"
        f"Actividad: {profile.activity_level}\n"
        f"Objetivo: {profile.goal}\n"
        f"TDEE estimado: ~{tdee} kcal/día",
        parse_mode="Markdown",
    )
    await log_interaction(int(chat_id), "/perfil", True)


# ─────────────────────────────────────────────────────────────── /salud ──────

@authorized_only
async def cmd_salud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra métricas de salud manualmente. Uso: /salud sueno:7 estres:medio pasos:8000"""

    chat_id = str(update.effective_chat.id)
    args_text = " ".join(context.args or [])

    if not args_text:
        await update.message.reply_text(
            "❌ Falta información. Ejemplo:\n`/salud sueno:7 estres:medio pasos:8000`",
            parse_mode="Markdown",
        )
        return

    try:
        data = parse_health_input(args_text)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        await log_interaction(int(chat_id), "/salud", False, str(e))
        return

    # Convertir al formato del dominio
    sleep_score = None
    if "sleep_hours" in data:
        sleep_score = min((data["sleep_hours"] / 8.0) * 100, 100.0)

    stress_level_float = None
    if "stress_level" in data:
        stress_level_float = _STRESS_FLOAT.get(data["stress_level"], 5.0)

    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)

        health_repo = HealthRepository(session)
        log = HealthLog(
            id=0,
            user_id=profile.id if profile else 0,
            date=date.today(),
            sleep_score=sleep_score,
            stress_level=stress_level_float,
            hrv=None,
            steps=data.get("steps"),
            mood=None,
            notes=None,
            source="manual",
            created_at=datetime.utcnow(),
        )
        await health_repo.log_health(log)

    tdee_msg = ""
    if profile:
        tdee = _estimate_tdee(profile.weight_kg, profile.height_cm, profile.age, profile.activity_level)
        tdee_msg = f"\n🔥 TDEE estimado: ~{tdee} kcal/día"

    lines = ["✅ Datos de salud registrados."]
    if sleep_score is not None:
        lines.append(f"😴 Sueño: {data['sleep_hours']}h (score: {sleep_score:.0f}/100)")
    if stress_level_float is not None:
        lines.append(f"😤 Estrés: {data['stress_level']} ({stress_level_float}/10)")
    if "steps" in data:
        lines.append(f"👟 Pasos: {data['steps']:,}")
    lines.append(tdee_msg)

    await update.message.reply_text("\n".join(lines))
    await log_interaction(int(chat_id), "/salud", True, str(data))


# ────────────────────────────────────────────────────────────── /precio ──────

@authorized_only
async def cmd_precio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra el precio de un ingrediente. Uso: /precio tomate 1500"""

    chat_id = str(update.effective_chat.id)
    args_text = " ".join(context.args or [])

    if not args_text:
        await update.message.reply_text(
            "❌ Uso: `/precio <ingrediente> <precio>`\nEjemplo: `/precio tomate 1500`",
            parse_mode="Markdown",
        )
        return

    try:
        ingredient_name, price = parse_price_input(args_text)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        await log_interaction(int(chat_id), "/precio", False, str(e))
        return

    async with get_session() as session:
        ing_repo = IngredientRepository(session)
        matches = await ing_repo.search_ingredients(ingredient_name)

        if not matches:
            await update.message.reply_text(
                f"❌ No encontré '*{ingredient_name}*'.\n"
                f"¿Querés crearlo? Usá la API o /ayuda para más info.",
                parse_mode="Markdown",
            )
            await log_interaction(int(chat_id), "/precio", False, f"Ingrediente no encontrado: {ingredient_name}")
            return

        ingredient = matches[0]
        market_repo = MarketRepository(session)
        price_obj = MarketPrice(
            id=0,
            ingredient_id=ingredient.id,
            price_ars=price,
            source="manual",
            store=None,
            confidence=1.0,
            date=date.today(),
            created_at=datetime.utcnow(),
        )
        await market_repo.add_price(price_obj)

    await update.message.reply_text(
        f"✅ Precio actualizado:\n*{ingredient.name.capitalize()}* → {_format_ars(price)} ARS/{ingredient.unit}",
        parse_mode="Markdown",
    )
    await log_interaction(int(chat_id), "/precio", True, f"{ingredient_name}={price}")


# ────────────────────────────────────────────────────────────── /pantry ──────

@authorized_only
async def cmd_pantry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista el inventario actual de la despensa."""

    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)
        if profile is None:
            await update.message.reply_text("❌ Primero configurá tu perfil con /setup.")
            return

        market_repo = MarketRepository(session)
        items = await market_repo.get_pantry(profile.id)

    if not items:
        await update.message.reply_text(
            "🏠 Tu alacena está vacía.\n"
            "Usá `/agregar_pantry <ingrediente> <cantidad> <unidad>` para agregar.",
            parse_mode="Markdown",
        )
        return

    lines = ["🏠 *Tu alacena:*"]
    for item in items:
        lines.append(f"• Ingrediente #{item.ingredient_id}: {item.quantity_amount} {item.unit}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/pantry", True, f"{len(items)} items")


# ─────────────────────────────────────────────── /agregar_pantry ──────

@authorized_only
async def cmd_agregar_pantry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Agrega un ítem a la despensa. Uso: /agregar_pantry arroz 2 kg"""

    chat_id = str(update.effective_chat.id)
    args_text = " ".join(context.args or [])

    if not args_text:
        await update.message.reply_text(
            "❌ Uso: `/agregar_pantry <ingrediente> <cantidad> <unidad>`\n"
            "Ejemplo: `/agregar_pantry arroz 2 kg`",
            parse_mode="Markdown",
        )
        return

    try:
        ingredient_name, quantity, unit = parse_pantry_input(args_text)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)
        if profile is None:
            await update.message.reply_text("❌ Primero configurá tu perfil con /setup.")
            return

        ing_repo = IngredientRepository(session)
        matches = await ing_repo.search_ingredients(ingredient_name)
        if not matches:
            await update.message.reply_text(
                f"❌ No encontré '*{ingredient_name}*' en el catálogo.",
                parse_mode="Markdown",
            )
            return

        ingredient = matches[0]
        market_repo = MarketRepository(session)
        item = PantryItem(
            id=0,
            user_id=profile.id,
            ingredient_id=ingredient.id,
            quantity_amount=quantity,
            unit=unit,
            expires_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await market_repo.update_pantry(item)

    await update.message.reply_text(
        f"✅ Alacena actualizada:\n*{ingredient.name.capitalize()}*: {quantity} {unit}",
        parse_mode="Markdown",
    )
    await log_interaction(int(chat_id), "/agregar_pantry", True, f"{ingredient_name}={quantity}{unit}")


# ─────────────────────────────────────────────────────────────── /estado ──────

@authorized_only
async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra un resumen general del estado del sistema."""

    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)

        profile_status = "✅" if profile else "❌"
        user_id = profile.id if profile else 0

        health_log = None
        pantry_count = 0
        active_plan = None

        if profile:
            health_repo = HealthRepository(session)
            health_log = await health_repo.get_latest_log(user_id)

            market_repo = MarketRepository(session)
            pantry = await market_repo.get_pantry(user_id)
            pantry_count = len(pantry)

            current_prices = await market_repo.get_all_current_prices()
            prices_count = len(current_prices)

            plan_repo = PlanningRepository(session)
            active_plan = await plan_repo.get_active_plan(user_id)
        else:
            prices_count = 0

    health_str = health_log.date.strftime("%d/%m/%Y") if health_log else "sin datos"
    plan_str = (
        f"✅ semana del {active_plan.week_start.strftime('%d/%m')}"
        if active_plan
        else "sin plan"
    )

    await update.message.reply_text(
        f"📊 *Estado del sistema*\n\n"
        f"👤 Perfil: {profile_status}\n"
        f"❤️ Último log de salud: {health_str}\n"
        f"📅 Plan activo: {plan_str}\n"
        f"🏠 Items en alacena: {pantry_count}\n"
        f"💰 Ingredientes con precio: {prices_count}",
        parse_mode="Markdown",
    )
    await log_interaction(int(chat_id), "/estado", True)


# ─────────────────────────────────────────────────────────────── /ayuda ──────

@authorized_only
async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista todos los comandos disponibles."""
    text = (
        "🤖 *SGAI — Comandos disponibles*\n\n"
        "/start — Bienvenida y estado rápido\n"
        "/perfil — Ver tu perfil nutricional\n"
        "/setup — Crear o actualizar tu perfil\n"
        "/estado — Resumen general del sistema\n\n"
        "📊 *Salud*\n"
        "/salud sueno:7 estres:medio pasos:8000 — Registrar métricas\n\n"
        "💰 *Precios*\n"
        "/precio <ingrediente> <precio> — Registrar precio\n"
        "  Ejemplo: /precio tomate 1500\n\n"
        "🏠 *Alacena*\n"
        "/pantry — Ver tu alacena\n"
        "/agregar\\_pantry <ingrediente> <cantidad> <unidad>\n"
        "  Ejemplo: /agregar\\_pantry arroz 2 kg\n\n"
        "❌ /cancelar — Abortar conversación activa"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
    await log_interaction(int(update.effective_chat.id), "/ayuda", True)


# ──────────────────────────────────────── Factory ──────

def create_telegram_bot() -> Application:
    """Crea y configura la aplicación del bot de Telegram."""
    from app.config import get_settings

    settings = get_settings()
    application = Application.builder().token(settings.telegram_bot_token).build()

    # Conversation handler primero (tiene prioridad sobre handlers simples)
    application.add_handler(build_setup_handler())

    # Comandos simples
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("perfil", cmd_perfil))
    application.add_handler(CommandHandler("salud", cmd_salud))
    application.add_handler(CommandHandler("precio", cmd_precio))
    application.add_handler(CommandHandler("pantry", cmd_pantry))
    application.add_handler(CommandHandler("agregar_pantry", cmd_agregar_pantry))
    application.add_handler(CommandHandler("estado", cmd_estado))
    application.add_handler(CommandHandler("ayuda", cmd_ayuda))

    logger.info("Telegram bot configured with %d handlers", len(application.handlers))
    return application
