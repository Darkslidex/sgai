"""
Parsers de input de texto para comandos del bot de Telegram.
Todas las funciones son puras (sin efectos secundarios) para facilitar el testing.
"""

# Aliases de campos para parse_health_input
_SLEEP_ALIASES = {"sueno", "sueño", "sleep"}
_STRESS_ALIASES = {"estres", "estrés", "stress"}
_STEPS_ALIASES = {"pasos", "steps"}
_CALORIES_ALIASES = {"cal", "calorias", "calorías", "calories"}

# Mapeo de valores de estrés en español/inglés → valor normalizado
_STRESS_VALUES = {
    "bajo": "low", "baja": "low", "low": "low",
    "medio": "medium", "media": "medium", "medium": "medium",
    "alto": "high", "alta": "high", "high": "high",
    "critico": "critical", "crítico": "critical", "critical": "critical",
}


def parse_health_input(text: str) -> dict:
    """
    Parsea pares clave:valor del comando /salud.

    Ejemplo: 'sueno:7 estres:medio pasos:8000 cal:2100'
    Retorna: {'sleep_hours': 7.0, 'stress_level': 'medium', 'steps': 8000, 'calories_burned': 2100.0}

    Aliases:
      sleep  → sueno, sueño, sleep   (rango 0-24)
      stress → estres, estrés, stress (bajo/medio/alto/critico o low/medium/high/critical)
      steps  → pasos, steps           (entero ≥ 0)
      cals   → cal, calorias, calorías, calories

    Lanza ValueError con mensaje descriptivo si el input es inválido.
    """
    result: dict = {}
    tokens = text.strip().split()

    for token in tokens:
        if ":" not in token:
            raise ValueError(f"Token inválido '{token}'. Formato esperado: clave:valor")
        key_raw, _, value_raw = token.partition(":")
        key = key_raw.strip().lower()
        value = value_raw.strip().lower()

        if key in _SLEEP_ALIASES:
            try:
                hours = float(value)
            except ValueError:
                raise ValueError(f"Valor de sueño inválido: '{value}'. Debe ser un número (horas).")
            if not (0 <= hours <= 24):
                raise ValueError(f"Horas de sueño fuera de rango: {hours}. Debe estar entre 0 y 24.")
            result["sleep_hours"] = hours

        elif key in _STRESS_ALIASES:
            normalized = _STRESS_VALUES.get(value)
            if normalized is None:
                raise ValueError(
                    f"Nivel de estrés inválido: '{value}'. "
                    f"Valores válidos: bajo, medio, alto, critico."
                )
            result["stress_level"] = normalized

        elif key in _STEPS_ALIASES:
            try:
                steps = int(float(value))
            except ValueError:
                raise ValueError(f"Valor de pasos inválido: '{value}'. Debe ser un número entero.")
            if steps < 0:
                raise ValueError(f"Pasos no puede ser negativo: {steps}.")
            result["steps"] = steps

        elif key in _CALORIES_ALIASES:
            try:
                cals = float(value)
            except ValueError:
                raise ValueError(f"Valor de calorías inválido: '{value}'. Debe ser un número.")
            if cals < 0:
                raise ValueError(f"Calorías no puede ser negativo: {cals}.")
            result["calories_burned"] = cals

        else:
            raise ValueError(
                f"Campo desconocido: '{key_raw}'. "
                f"Campos válidos: sueno, estres, pasos, cal."
            )

    if not result:
        raise ValueError("No se encontraron datos válidos. Formato: /salud sueno:7 estres:medio pasos:8000")

    return result


def parse_price_input(text: str) -> tuple[str, float]:
    """
    Parsea el argumento del comando /precio.

    Ejemplo: 'tomate 1500'          → ('tomate', 1500.0)
             'tomate perita 1800'   → ('tomate perita', 1800.0)

    El ÚLTIMO token numérico es el precio; todo lo anterior es el nombre del ingrediente.
    Lanza ValueError si no hay precio o el formato es inválido.
    """
    tokens = text.strip().split()
    if len(tokens) < 2:
        raise ValueError(
            "Formato inválido. Uso: /precio <ingrediente> <precio>\n"
            "Ejemplo: /precio tomate 1500"
        )

    # Buscar el último token numérico
    last = tokens[-1]
    try:
        price = float(last.replace(",", "."))
    except ValueError:
        raise ValueError(
            f"El precio '{last}' no es un número válido.\n"
            "Ejemplo: /precio tomate 1500"
        )

    if price <= 0:
        raise ValueError(f"El precio debe ser mayor a cero. Recibido: {price}")

    ingredient_name = " ".join(tokens[:-1]).strip().lower()
    return ingredient_name, price


def parse_pantry_input(text: str) -> tuple[str, float, str]:
    """
    Parsea el argumento del comando /agregar_pantry.

    Ejemplo: 'arroz 2 kg'  → ('arroz', 2.0, 'kg')

    Formato: <ingrediente> <cantidad> <unidad>
    El último token es la unidad, el penúltimo es la cantidad, el resto es el nombre.
    Lanza ValueError si faltan campos o el formato es inválido.
    """
    tokens = text.strip().split()
    if len(tokens) < 3:
        raise ValueError(
            "Formato inválido. Uso: /agregar_pantry <ingrediente> <cantidad> <unidad>\n"
            "Ejemplo: /agregar_pantry arroz 2 kg"
        )

    unit = tokens[-1].lower()
    qty_raw = tokens[-2]
    try:
        quantity = float(qty_raw.replace(",", "."))
    except ValueError:
        raise ValueError(
            f"La cantidad '{qty_raw}' no es un número válido.\n"
            "Ejemplo: /agregar_pantry arroz 2 kg"
        )

    if quantity <= 0:
        raise ValueError(f"La cantidad debe ser mayor a cero. Recibido: {quantity}")

    ingredient_name = " ".join(tokens[:-2]).strip().lower()
    return ingredient_name, quantity, unit
