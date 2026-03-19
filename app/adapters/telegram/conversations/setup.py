"""
ConversationHandler para el flujo /setup de creación de perfil de usuario.
Estados: NAME → WEIGHT → HEIGHT → ACTIVITY → GOAL → (crear perfil)
"""

import logging
from datetime import datetime

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.adapters.telegram.audit import log_interaction
from app.adapters.telegram.security import authorized_only

logger = logging.getLogger(__name__)

# Estados de la conversación
NAME, WEIGHT, HEIGHT, ACTIVITY, GOAL = range(5)

_ACTIVITY_OPTIONS = ["sedentario", "ligero", "moderado", "activo", "muy_activo"]
_ACTIVITY_MAP = {
    "sedentario": "sedentary",
    "ligero": "light",
    "moderado": "moderate",
    "activo": "active",
    "muy_activo": "very_active",
}
_GOAL_OPTIONS = ["mantener", "perder", "ganar"]
_GOAL_MAP = {"mantener": "maintain", "perder": "lose", "ganar": "gain"}


@authorized_only
async def start_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el flujo de configuración del perfil."""
    context.user_data.clear()
    await update.message.reply_text(
        "⚙️ *Configuración de perfil*\n\n"
        "Vamos a configurar tu perfil nutricional.\n"
        "Escribí /cancelar en cualquier momento para abortar.\n\n"
        "¿Cuál es tu nombre?",
        parse_mode="Markdown",
    )
    return NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if len(name) < 1 or len(name) > 100:
        await update.message.reply_text("❌ Nombre inválido. Ingresá entre 1 y 100 caracteres.")
        return NAME
    context.user_data["name"] = name
    await update.message.reply_text(f"👋 Hola, {name}!\n\n¿Cuál es tu peso actual en kg? (ej: 75.5)")
    return WEIGHT


async def receive_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        weight = float(update.message.text.replace(",", "."))
        if not (20 < weight < 500):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Peso inválido. Ingresá un número entre 20 y 500 kg.")
        return WEIGHT
    context.user_data["weight_kg"] = weight
    await update.message.reply_text(f"✅ Peso: {weight} kg\n\n¿Cuál es tu altura en cm? (ej: 175)")
    return HEIGHT


async def receive_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        height = float(update.message.text.replace(",", "."))
        if not (100 < height < 300):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Altura inválida. Ingresá un número entre 100 y 300 cm.")
        return HEIGHT
    context.user_data["height_cm"] = height
    keyboard = [[opt] for opt in _ACTIVITY_OPTIONS]
    await update.message.reply_text(
        f"✅ Altura: {height} cm\n\n¿Cuál es tu nivel de actividad física?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ACTIVITY


async def receive_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = update.message.text.strip().lower()
    if value not in _ACTIVITY_MAP:
        await update.message.reply_text(
            f"❌ Opción inválida. Elegí: {', '.join(_ACTIVITY_OPTIONS)}"
        )
        return ACTIVITY
    context.user_data["activity_level"] = _ACTIVITY_MAP[value]
    keyboard = [[opt] for opt in _GOAL_OPTIONS]
    await update.message.reply_text(
        "¿Cuál es tu objetivo?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return GOAL


async def receive_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el objetivo y crea el perfil en la base de datos."""
    from app.adapters.persistence.user_repo import UserRepository
    from app.database import get_session
    from app.domain.models.user import UserProfile

    value = update.message.text.strip().lower()
    if value not in _GOAL_MAP:
        await update.message.reply_text(
            f"❌ Opción inválida. Elegí: {', '.join(_GOAL_OPTIONS)}"
        )
        return GOAL

    context.user_data["goal"] = _GOAL_MAP[value]
    chat_id = str(update.effective_chat.id)
    data = context.user_data

    try:
        async with get_session() as session:
            repo = UserRepository(session)
            existing = await repo.get_profile_by_chat_id(chat_id)
            profile = UserProfile(
                id=0,
                telegram_chat_id=chat_id,
                name=data["name"],
                age=42,  # Default — se actualiza vía /perfil luego
                weight_kg=data["weight_kg"],
                height_cm=data["height_cm"],
                activity_level=data["activity_level"],
                goal=data["goal"],
                max_storage_volume={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            if existing:
                profile = UserProfile(
                    id=existing.id,
                    telegram_chat_id=existing.telegram_chat_id,
                    name=data["name"],
                    age=existing.age,
                    weight_kg=data["weight_kg"],
                    height_cm=data["height_cm"],
                    activity_level=data["activity_level"],
                    goal=data["goal"],
                    max_storage_volume=existing.max_storage_volume,
                    created_at=existing.created_at,
                    updated_at=datetime.utcnow(),
                )
                await repo.update_profile(profile)
                action = "actualizado"
            else:
                await repo.create_profile(profile)
                action = "creado"

        await update.message.reply_text(
            f"✅ Perfil {action} exitosamente!\n\n"
            f"👤 Nombre: {data['name']}\n"
            f"⚖️ Peso: {data['weight_kg']} kg\n"
            f"📏 Altura: {data['height_cm']} cm\n"
            f"🏃 Actividad: {value}\n"
            f"🎯 Objetivo: {value}\n\n"
            "Usá /estado para ver un resumen completo.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await log_interaction(int(chat_id), "/setup", True, f"Perfil {action}")

    except Exception as e:
        logger.error("Error creando perfil en /setup: %s", e)
        await update.message.reply_text(
            "❌ Error al guardar el perfil. Intentá de nuevo con /setup.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await log_interaction(int(chat_id), "/setup", False, str(e))

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Configuración cancelada. Usá /setup cuando quieras.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("❓ No entendí ese valor. Ingresá un valor válido o /cancelar para abortar.")


def build_setup_handler() -> ConversationHandler:
    """Construye y retorna el ConversationHandler para /setup."""
    return ConversationHandler(
        entry_points=[CommandHandler("setup", start_setup)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_weight)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_height)],
            ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_activity)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_goal)],
        },
        fallbacks=[
            CommandHandler("cancelar", cancel_setup),
            MessageHandler(filters.COMMAND, cancel_setup),
        ],
        allow_reentry=True,
    )
