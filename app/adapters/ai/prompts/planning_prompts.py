"""
Prompts de 3 capas para el Chef Ejecutivo de SGAI.

Capa 1 — System: rol fijo del Chef
Capa 2 — Context: información dinámica del usuario
Capa 3 — Task: la tarea concreta a ejecutar
"""

from app.domain.ports.ai_planner_port import PlanningContext

SYSTEM_PROMPT = """\
Eres el Chef Ejecutivo de SGAI, especializado en Batch Cooking 1x5 para Buenos Aires, Argentina.

Tu trabajo: crear planes de alimentación para cocinar 1 vez y comer 5 días.
Responder SIEMPRE en JSON válido, sin texto adicional antes ni después del JSON.

REGLAS OBLIGATORIAS:
- Todas las recetas deben ser recalentables hasta 5 días de refrigeración
- Maximizar solapamiento de ingredientes entre recetas del mismo plan (reducir compras)
- Respetar estrictamente las restricciones alimentarias del usuario
- Precios en ARS (pesos argentinos)
- La lista de compras debe descontar lo que el usuario ya tiene en la alacena
- No sugerir ingredientes que el usuario ya tiene en suficiente cantidad
- Batching realista: si el usuario vive solo, pensar en porciones individuales

JSON SCHEMA REQUERIDO:
{
  "days": [
    {"day": "Lunes", "lunch": "Nombre receta almuerzo", "dinner": "Nombre receta cena"},
    {"day": "Martes", "lunch": "...", "dinner": "..."},
    {"day": "Miércoles", "lunch": "...", "dinner": "..."},
    {"day": "Jueves", "lunch": "...", "dinner": "..."},
    {"day": "Viernes", "lunch": "...", "dinner": "..."}
  ],
  "shopping_list": [
    {"ingredient_name": "pollo", "quantity": 2.0, "unit": "kg", "estimated_price_ars": 2400.0}
  ],
  "total_cost_ars": 15000.0,
  "cooking_day": "Domingo",
  "prep_steps": [
    "1. Cocinar arroz integral (30 min)",
    "2. Marinar y hornear pollo (45 min)"
  ]
}
"""


def build_context_prompt(context: PlanningContext) -> str:
    """Capa 2: información dinámica del usuario."""

    # Restricciones alimentarias
    restrictions = [p.value for p in context.preferences if p.key == "restriction"]
    restrictions_str = ", ".join(restrictions) if restrictions else "ninguna"

    # Alacena (lo que ya tiene)
    pantry_lines = []
    for item in context.pantry:
        pantry_lines.append(f"  - Ingrediente #{item.ingredient_id}: {item.quantity_amount} {item.unit}")
    pantry_str = "\n".join(pantry_lines) if pantry_lines else "  (vacía)"

    # Precios disponibles (top 20 para no saturar el contexto)
    price_lines = []
    for ing, price in context.priced_ingredients[:20]:
        price_lines.append(f"  - {ing.name}: ${price.price_ars:.0f}/{ing.unit}")
    price_str = "\n".join(price_lines) if price_lines else "  (sin precios cargados)"

    # Historial de planes (evitar repetición)
    history_str = "ninguno"
    if context.plan_history:
        recent = context.plan_history[0]
        plan_data = recent.plan_json
        days = plan_data.get("days", [])
        recipes = set()
        for day in days:
            recipes.add(day.get("lunch", ""))
            recipes.add(day.get("dinner", ""))
        recipes.discard("")
        if recipes:
            history_str = ", ".join(list(recipes)[:6])

    # Capacidad de almacenamiento (ADR-008)
    storage = context.profile.max_storage_volume
    storage_str = (
        f"refrigerados: {storage.get('refrigerados', '?')}L, "
        f"secos: {storage.get('secos', '?')}L, "
        f"congelados: {storage.get('congelados', '?')}L"
    ) if storage else "no configurada"

    return f"""\
PERFIL DEL USUARIO:
- Nombre: {context.profile.name}
- Edad: {context.profile.age} años
- Peso: {context.profile.weight_kg} kg, Altura: {context.profile.height_cm} cm
- Actividad: {context.profile.activity_level}, Objetivo: {context.profile.goal}
- TDEE estimado: {context.tdee_kcal} kcal/día
- Restricciones alimentarias: {restrictions_str}
- Capacidad de almacenamiento (ADR-008): {storage_str}

ALACENA ACTUAL (no incluir en lista de compras):
{pantry_str}

PRECIOS ACTUALES DISPONIBLES:
{price_str}

PLANES ANTERIORES (evitar repetir estas recetas):
{history_str}
"""


TASK_PROMPT = """\
Con el perfil y contexto anterior, generá:
1. Plan semanal de 5 días (lunes a viernes), almuerzo y cena cada día
2. Lista de compras consolidada con precios estimados en ARS
3. Día de cocción recomendado y pasos de preparación en orden

Responder ÚNICAMENTE con el JSON según el schema definido.
"""
