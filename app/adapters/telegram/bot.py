"""
Bot de Telegram principal del SGAI.
Maneja comandos de texto. Todos los handlers están protegidos por authorized_only.
"""

import logging
from datetime import date, datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.adapters.ai.deepseek_adapter import DeepSeekAdapter
from app.adapters.persistence.health_repo import HealthRepository
from app.adapters.persistence.ingredient_repo import IngredientRepository
from app.adapters.persistence.market_repo import MarketRepository
from app.adapters.persistence.planning_repo import PlanningRepository
from app.adapters.persistence.user_repo import UserRepository
from app.adapters.telegram.audit import log_interaction
from app.adapters.telegram.conversations.setup import build_setup_handler
from app.adapters.telegram.parsers import parse_health_input, parse_pantry_input, parse_price_input
from app.adapters.telegram.security import authorized_only
from app.config import get_settings
from app.database import get_session
from app.domain.models.health import HealthLog
from app.domain.models.market import MarketPrice
from app.domain.models.pantry_item import PantryItem
from app.domain.services.consumption_ratio_service import ConsumptionRatioService
from app.domain.services.energy_mode_service import EnergyModeService, EnergyState
from app.domain.services.health_service import HealthService
from app.domain.services.pantry_service import PantryService
from app.domain.services.planning_service import PlanningService
from app.domain.services.swap_service import SwapService

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


# ──────────────────────────────────────────────────────────────── /plan ──────

@authorized_only
async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Genera o muestra el plan semanal activo. Uso: /plan [--forzar]"""

    chat_id = str(update.effective_chat.id)
    force = "--forzar" in (context.args or [])

    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)

        if profile is None:
            await update.message.reply_text("❌ Primero configurá tu perfil con /setup.")
            return

        await update.message.reply_text("⏳ Consultando tu plan semanal...")

        try:
            settings = get_settings()
            adapter = DeepSeekAdapter(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                model=settings.deepseek_model,
            )
            market_repo = MarketRepository(session)
            planning_repo = PlanningRepository(session)
            ing_repo = IngredientRepository(session)

            service = PlanningService(user_repo, market_repo, planning_repo, adapter, ing_repo)
            plan = await service.get_or_generate_plan(profile.id, force=force)

        except Exception as exc:
            logger.error("Error generando plan para chat_id=%s: %s", chat_id, exc)
            await update.message.reply_text(f"❌ Error al generar el plan: {exc}")
            await log_interaction(int(chat_id), "/plan", False, str(exc))
            return

    days = plan.plan_json.get("days", [])
    lines = [f"📅 *Plan semanal* — semana del {plan.week_start.strftime('%d/%m/%Y')}\n"]
    for d in days:
        lines.append(f"*{d['day']}*")
        lines.append(f"  🍽 Almuerzo: {d['lunch']}")
        lines.append(f"  🌙 Cena: {d['dinner']}")
    lines.append(f"\n💰 Costo estimado: {_format_ars(plan.total_cost_ars)} ARS")
    lines.append("Usá /mi\\_plan para ver la lista de compras.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/plan", True, f"cost={plan.total_cost_ars:.0f}")


# ────────────────────────────────────────────────────────────── /mi_plan ──────

@authorized_only
async def cmd_mi_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el resumen del plan activo con lista de compras."""

    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)
        if profile is None:
            await update.message.reply_text("❌ Primero configurá tu perfil con /setup.")
            return

        planning_repo = PlanningRepository(session)
        plan = await planning_repo.get_active_plan(profile.id)

    if plan is None:
        await update.message.reply_text(
            "📋 No tenés un plan activo.\nUsá /plan para generar uno."
        )
        return

    items = plan.shopping_list_json.get("items", [])
    cooking_day = plan.plan_json.get("cooking_day", "?")

    lines = [f"🛒 *Lista de compras* — semana del {plan.week_start.strftime('%d/%m/%Y')}\n"]
    for item in items:
        price_str = _format_ars(item["estimated_price_ars"])
        lines.append(f"• {item['ingredient_name'].capitalize()}: {item['quantity']} {item['unit']} (~{price_str})")

    lines.append(f"\n💰 *Total estimado: {_format_ars(plan.total_cost_ars)} ARS*")
    lines.append(f"🍳 Día de cocción sugerido: {cooking_day}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/mi_plan", True)


# ──────────────────────────────────────────────────────────────── /swap ──────

@authorized_only
async def cmd_swap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sugiere sustitutos para un ingrediente. Uso: /swap pollo"""

    chat_id = str(update.effective_chat.id)
    ingredient_name = " ".join(context.args or "").strip()

    if not ingredient_name:
        await update.message.reply_text(
            "❌ Uso: `/swap <ingrediente>`\nEjemplo: `/swap pollo`",
            parse_mode="Markdown",
        )
        return

    async with get_session() as session:
        ing_repo = IngredientRepository(session)
        market_repo = MarketRepository(session)

        matches = await ing_repo.search_ingredients(ingredient_name)
        if not matches:
            await update.message.reply_text(f"❌ No encontré '*{ingredient_name}*' en el catálogo.", parse_mode="Markdown")
            return

        original = matches[0]
        swap_service = SwapService(ing_repo, market_repo)
        suggestions = await swap_service.suggest_swap(original.id)

    if not suggestions:
        await update.message.reply_text(
            f"No encontré alternativas para *{original.name}* en la misma categoría con precio disponible.",
            parse_mode="Markdown",
        )
        return

    lines = [f"🔄 *Alternativas para {original.name.capitalize()}* (Categoría: {original.category})\n"]
    for i, s in enumerate(suggestions, 1):
        delta_costo = f"+{_format_ars(s.cost_delta_ars)}" if s.cost_delta_ars >= 0 else f"-{_format_ars(abs(s.cost_delta_ars))}"
        delta_prot = f"+{s.protein_delta_g:.1f}g" if s.protein_delta_g >= 0 else f"{s.protein_delta_g:.1f}g"
        lines.append(
            f"*{i}. {s.ingredient.name.capitalize()}*\n"
            f"   💰 {_format_ars(s.current_price_ars)} ARS ({delta_costo})\n"
            f"   💪 {s.protein_per_100g:.1f}g prot/100g ({delta_prot})\n"
            f"   ⚡ Eficiencia: {s.efficiency_score:.0f}/100\n"
            f"   📝 {s.reason}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/swap", True, ingredient_name)


# ─────────────────────────────────────────────────────────── /eficiencia ──────

@authorized_only
async def cmd_eficiencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el ranking de ingredientes por eficiencia nutricional (costo/proteína)."""

    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        ing_repo = IngredientRepository(session)
        market_repo = MarketRepository(session)
        swap_service = SwapService(ing_repo, market_repo)
        ranking = await swap_service.get_efficiency_ranking(limit=10)

    if not ranking:
        await update.message.reply_text(
            "⚠️ No hay ingredientes con precio y proteína cargados.\n"
            "Usá /precio para registrar precios."
        )
        return

    lines = ["⚡ *Ranking de Eficiencia Nutricional* (ADR-008)\n_proteína/costo, mayor = mejor_\n"]
    medals = ["🥇", "🥈", "🥉"] + ["  "] * 10
    for i, (ing, score, price_ars) in enumerate(ranking):
        lines.append(
            f"{medals[i]} *{ing.name.capitalize()}*\n"
            f"   Score: {score:.2f} | {ing.protein_per_100g:.1f}g prot/100g | {_format_ars(price_ars)}/unidad"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/eficiencia", True, f"{len(ranking)} items")


# ──────────────────────────────────────────────────────────────── /tdee ──────

@authorized_only
async def cmd_tdee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el TDEE dinámico con ajustes por biomarcadores."""

    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)

        if profile is None:
            await update.message.reply_text("❌ Primero configurá tu perfil con /setup.")
            return

        health_repo = HealthRepository(session)
        metrics = await health_repo.get_latest_log(profile.id)

    service = HealthService()
    result = service.calculate_tdee(profile, metrics)
    b = result.breakdown

    lines = [
        f"🔥 *Tu TDEE dinámico* (Harris-Benedict)\n",
        f"⚖️ Peso: {profile.weight_kg} kg | Altura: {profile.height_cm} cm | Edad: {profile.age} años",
        f"💪 Actividad: {profile.activity_level} (×{result.activity_multiplier})",
        f"🎯 Objetivo: {profile.goal} (×{result.goal_multiplier})",
        f"\n📊 Desglose:",
        f"  BMR base: {b['bmr_kcal']} kcal",
        f"  + Actividad: {b['after_activity']} kcal",
        f"  + Objetivo: {b['after_goal']} kcal",
    ]

    if result.stress_adjustment != 0.0:
        lines.append(f"  😤 Estrés alto: {b['stress_adjustment_pct']}%")
    if result.sleep_adjustment != 0.0:
        lines.append(f"  😴 Sueño pobre: {b['sleep_adjustment_pct']}%")
    if b["total_adjustment_pct"] != 0:
        lines.append(f"  Total ajuste dinámico: {b['total_adjustment_pct']}%")

    lines.append(f"\n🔥 *TDEE final: {result.tdee} kcal/día*")

    if metrics is None:
        lines.append("\n_Sin datos biométricos recientes. Usá /salud para registrar métricas._")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/tdee", True, f"tdee={result.tdee}")


# ──────────────────────────────────────────────────────────────── /energia ──────

@authorized_only
async def cmd_energia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el estado energético actual basado en biomarcadores (ADR-008)."""

    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)

        if profile is None:
            await update.message.reply_text("❌ Primero configurá tu perfil con /setup.")
            return

        health_repo = HealthRepository(session)
        metrics = await health_repo.get_latest_log(profile.id)

    energy_service = EnergyModeService()
    state = await energy_service.evaluate_energy_state(profile.id, metrics)

    _icons = {
        EnergyState.NORMAL: "✅",
        EnergyState.LOW: "⚠️",
        EnergyState.CRITICAL: "🚨",
    }
    _labels = {
        EnergyState.NORMAL: "Normal",
        EnergyState.LOW: "Baja Energía",
        EnergyState.CRITICAL: "Crítico",
    }
    _tips = {
        EnergyState.NORMAL: "Flujo completo disponible. Podés cocinar con normalidad.",
        EnergyState.LOW: "Modo Baja Energía activo. Te sugiero recetas de ≤10 min.\nUsá /plan para ver opciones rápidas.",
        EnergyState.CRITICAL: "Energía muy baja. Solo recalentá lo que ya tenés preparado.\nDescansá — el batch cooking hace su trabajo.",
    }

    icon = _icons[state]
    label = _labels[state]
    tip = _tips[state]

    lines = [f"{icon} *Estado energético: {label}*\n", tip]

    if metrics is not None:
        lines.append("\n📊 *Biomarcadores actuales:*")
        if metrics.hrv is not None:
            hrv_note = " (bajo)" if metrics.hrv < energy_service.HRV_LOW_THRESHOLD else " (normal)"
            lines.append(f"  ❤️ HRV: {metrics.hrv:.0f} ms{hrv_note}")
        if metrics.sleep_score is not None:
            sleep_note = " (pobre)" if metrics.sleep_score < energy_service.SLEEP_POOR_THRESHOLD else " (normal)"
            lines.append(f"  😴 Sueño: {metrics.sleep_score:.0f}/100{sleep_note}")
        if metrics.stress_level is not None:
            stress_note = " (alto)" if metrics.stress_level > energy_service.STRESS_HIGH_THRESHOLD else " (normal)"
            lines.append(f"  😤 Estrés: {metrics.stress_level:.1f}/10{stress_note}")
    else:
        lines.append("\n_Sin datos biométricos recientes. Usá /salud hrv:45 para registrar._")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/energia", True, state.value)


# ──────────────────────────────────────────────────────────────── /precios ──────

@authorized_only
async def cmd_precios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista los precios actuales de ingredientes del plan activo."""
    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)
        if profile is None:
            await update.message.reply_text("❌ Primero configurá tu perfil con /setup.")
            return

        market_repo = MarketRepository(session)
        planning_repo = PlanningRepository(session)
        ing_repo = IngredientRepository(session)

        active_plan = await planning_repo.get_active_plan(profile.id)
        if active_plan is None:
            await update.message.reply_text("📋 No tenés un plan activo. Usá /plan para generar uno.")
            return

        all_prices = await market_repo.get_all_current_prices()
        price_map = {p.ingredient_id: p for p in all_prices}

        items = active_plan.shopping_list_json.get("items", [])
        lines = [f"💰 *Precios — semana del {active_plan.week_start.strftime('%d/%m')}*\n"]
        shown = 0
        for item in items[:15]:
            matches = await ing_repo.search_ingredients(item["ingredient_name"])
            if not matches:
                continue
            ing = matches[0]
            price = price_map.get(ing.id)
            if price:
                source_icon = {"manual": "✋", "sepa": "🏛", "scraping": "🌐", "seed": "📦"}.get(price.source, "❓")
                conf_str = f"{price.confidence:.0%}"
                lines.append(
                    f"• {ing.name.capitalize()}: {_format_ars(price.price_ars)}/{ing.unit} "
                    f"{source_icon} {conf_str}"
                )
                shown += 1

    if shown == 0:
        lines.append("_Sin precios cargados. Usá /precio para registrar._")
    lines.append("\n✋ Manual  🏛 SEPA  🌐 Scraping  📦 Seed")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/precios", True, f"{shown} precios")


# ───────────────────────────────────────────────────── /precio_detalle ──────

@authorized_only
async def cmd_precio_detalle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Historial de precios de un ingrediente. Uso: /precio_detalle tomate"""
    chat_id = str(update.effective_chat.id)
    ingredient_name = " ".join(context.args or "").strip()

    if not ingredient_name:
        await update.message.reply_text(
            "❌ Uso: `/precio_detalle <ingrediente>`\nEjemplo: `/precio_detalle tomate`",
            parse_mode="Markdown",
        )
        return

    async with get_session() as session:
        ing_repo = IngredientRepository(session)
        matches = await ing_repo.search_ingredients(ingredient_name)
        if not matches:
            await update.message.reply_text(f"❌ No encontré '*{ingredient_name}*'.", parse_mode="Markdown")
            return

        ing = matches[0]
        market_repo = MarketRepository(session)
        history = await market_repo.get_price_history(ing.id, days=30)

    if not history:
        await update.message.reply_text(
            f"_No hay historial de precios para *{ing.name}* en los últimos 30 días._",
            parse_mode="Markdown",
        )
        return

    lines = [f"📊 *Historial: {ing.name.capitalize()}* (últimos 30 días)\n"]
    for p in history[:10]:
        source_icon = {"manual": "✋", "sepa": "🏛", "scraping": "🌐", "seed": "📦"}.get(p.source, "❓")
        store_str = f" — {p.store}" if p.store else ""
        lines.append(
            f"• {p.date.strftime('%d/%m')} {source_icon}{store_str}: "
            f"{_format_ars(p.price_ars)} (conf. {p.confidence:.0%})"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/precio_detalle", True, ing.name)


# ─────────────────────────────────────────────────────── /vencimientos ──────

@authorized_only
async def cmd_vencimientos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Items próximos a vencer + items en riesgo de desperdicio (ADR-008)."""
    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)
        if profile is None:
            await update.message.reply_text("❌ Primero configurá tu perfil con /setup.")
            return

        market_repo = MarketRepository(session)
        ing_repo = IngredientRepository(session)
        planning_repo = PlanningRepository(session)

        pantry_service = PantryService(market_repo, ing_repo)
        consumption_service = ConsumptionRatioService(market_repo, planning_repo, ing_repo)

        expiring = await pantry_service.get_expiring_soon(profile.id, days=3)
        expired = await pantry_service.get_expired(profile.id)
        waste_report = await consumption_service.get_waste_risk_report(profile.id)
        at_risk = [w for w in waste_report if w.action in ("will_waste", "consume_soon")]

    lines = ["📅 *Vencimientos y Riesgo de Desperdicio*\n"]

    if expired:
        lines.append(f"🚨 *Vencidos ({len(expired)}) — descartar:*")
        for item in expired:
            lines.append(f"  • Ingrediente #{item.ingredient_id}: {item.quantity_amount} {item.unit}")

    if expiring:
        lines.append(f"\n⚠️ *Próximos a vencer en 3 días ({len(expiring)}):*")
        for item in expiring:
            days_left = ""
            if item.expires_at:
                delta = item.expires_at - datetime.utcnow()
                days_left = f" ({max(0, delta.days)}d)"
            lines.append(f"  • Ingrediente #{item.ingredient_id}: {item.quantity_amount} {item.unit}{days_left}")

    if at_risk:
        lines.append(f"\n⚠️ *Riesgo de desperdicio — ADR-008 ({len(at_risk)} items):*")
        for w in at_risk[:5]:
            icon = "🔴" if w.action == "will_waste" else "🟡"
            lines.append(
                f"  {icon} Ingrediente #{w.pantry_item.ingredient_id}: "
                f"{w.days_to_consume:.0f}d para consumir, {w.days_remaining}d útil"
            )
        lines.append("\n_Usá /desperdicio para el reporte completo._")

    if not expired and not expiring and not at_risk:
        lines.append("✅ Todo en orden — sin vencimientos ni riesgo de desperdicio.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/vencimientos", True)


# ──────────────────────────────────────────────────────────── /desperdicio ──────

@authorized_only
async def cmd_desperdicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reporte completo de riesgo de desperdicio del pantry (ADR-008)."""
    chat_id = str(update.effective_chat.id)
    async with get_session() as session:
        user_repo = UserRepository(session)
        profile = await user_repo.get_profile_by_chat_id(chat_id)
        if profile is None:
            await update.message.reply_text("❌ Primero configurá tu perfil con /setup.")
            return

        market_repo = MarketRepository(session)
        ing_repo = IngredientRepository(session)
        planning_repo = PlanningRepository(session)
        consumption_service = ConsumptionRatioService(market_repo, planning_repo, ing_repo)
        report = await consumption_service.get_waste_risk_report(profile.id)

    if not report:
        await update.message.reply_text("🏠 Tu alacena está vacía — sin riesgo de desperdicio.")
        return

    _action_icon = {"ok": "✅", "consume_soon": "🟡", "will_waste": "🔴"}
    _action_label = {"ok": "OK", "consume_soon": "Consumir pronto", "will_waste": "Riesgo alto"}

    lines = ["♻️ *Reporte de Riesgo de Desperdicio* (ADR-008)\n"]
    for w in report:
        icon = _action_icon.get(w.action, "❓")
        label = _action_label.get(w.action, w.action)
        risk_pct = f"{w.waste_risk * 100:.0f}%"
        lines.append(
            f"{icon} *Ingrediente #{w.pantry_item.ingredient_id}*\n"
            f"   {label} | Riesgo: {risk_pct}\n"
            f"   Vida útil: {w.days_remaining}d | Para consumir: {w.days_to_consume:.0f}d"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await log_interaction(int(chat_id), "/desperdicio", True, f"{len(report)} items")


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
        "🤖 *Planificación IA*\n"
        "/plan — Generar plan semanal Batch Cooking 1x5\n"
        "/plan --forzar — Forzar regeneración del plan\n"
        "/mi\\_plan — Ver lista de compras del plan activo\n"
        "/swap <ingrediente> — Sustitutos por eficiencia nutricional\n"
        "  Ejemplo: /swap pollo\n"
        "/eficiencia — Ranking ingredientes por costo/proteína (ADR-008)\n\n"
        "❤️ *Salud Dinámica*\n"
        "/tdee — TDEE dinámico con ajuste por estrés/sueño (Harris-Benedict)\n"
        "/energia — Estado energético actual (Normal/Baja Energía/Crítico) ADR-008\n\n"
        "💰 *Precios híbridos (ADR-004)*\n"
        "/precios — Precios actuales del plan activo (fuente + confidence)\n"
        "/precio\\_detalle <ingrediente> — Historial de precios últimos 30 días\n\n"
        "♻️ *Anti-desperdicio (ADR-008)*\n"
        "/vencimientos — Items próximos a vencer + riesgo de desperdicio\n"
        "/desperdicio — Reporte completo de riesgo de desperdicio\n\n"
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
    # Fase 2A — IA
    application.add_handler(CommandHandler("plan", cmd_plan))
    application.add_handler(CommandHandler("mi_plan", cmd_mi_plan))
    application.add_handler(CommandHandler("swap", cmd_swap))
    application.add_handler(CommandHandler("eficiencia", cmd_eficiencia))
    # Fase 3A — Salud Dinámica
    application.add_handler(CommandHandler("tdee", cmd_tdee))
    application.add_handler(CommandHandler("energia", cmd_energia))
    # Fase 3B — Precios híbridos + Pantry
    application.add_handler(CommandHandler("precios", cmd_precios))
    application.add_handler(CommandHandler("precio_detalle", cmd_precio_detalle))
    application.add_handler(CommandHandler("vencimientos", cmd_vencimientos))
    application.add_handler(CommandHandler("desperdicio", cmd_desperdicio))

    logger.info("Telegram bot configured with %d handlers", len(application.handlers))
    return application
