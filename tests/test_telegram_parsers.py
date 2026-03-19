"""Tests de los parsers de input del bot de Telegram (tests puros, sin PTB)."""

import pytest

from app.adapters.telegram.parsers import (
    parse_health_input,
    parse_pantry_input,
    parse_price_input,
)


# ─────────────────────────────── parse_health_input ───────────────────────────

def test_parse_health_input_full():
    """Parsea correctamente todos los campos con alias en español."""
    result = parse_health_input("sueno:7 estres:medio pasos:8000")
    assert result["sleep_hours"] == 7.0
    assert result["stress_level"] == "medium"
    assert result["steps"] == 8000


def test_parse_health_input_alias_accent():
    """sueño (con tilde) funciona igual que sueno."""
    result = parse_health_input("sueño:7")
    assert result["sleep_hours"] == 7.0


def test_parse_health_input_sleep_out_of_range():
    """sueno:25 → ValueError (supera el límite de 24h)."""
    with pytest.raises(ValueError, match="rango"):
        parse_health_input("sueno:25")


def test_parse_health_input_stress_invalid():
    """estres:invalido → ValueError."""
    with pytest.raises(ValueError, match="inválido"):
        parse_health_input("estres:invalido")


def test_parse_health_input_stress_aliases():
    """Todos los aliases de estrés funcionan correctamente."""
    assert parse_health_input("estres:bajo")["stress_level"] == "low"
    assert parse_health_input("estres:alto")["stress_level"] == "high"
    assert parse_health_input("estres:critico")["stress_level"] == "critical"
    assert parse_health_input("stress:high")["stress_level"] == "high"


def test_parse_health_input_calories():
    """Alias de calorías funciona."""
    result = parse_health_input("cal:2100")
    assert result["calories_burned"] == 2100.0


def test_parse_health_input_empty():
    """String vacío → ValueError."""
    with pytest.raises(ValueError):
        parse_health_input("")


# ─────────────────────────────── parse_price_input ────────────────────────────

def test_parse_price_single_word():
    """tomate 1500 → ('tomate', 1500.0)."""
    name, price = parse_price_input("tomate 1500")
    assert name == "tomate"
    assert price == 1500.0


def test_parse_price_multi_word():
    """tomate perita 1800 → ('tomate perita', 1800.0)."""
    name, price = parse_price_input("tomate perita 1800")
    assert name == "tomate perita"
    assert price == 1800.0


def test_parse_price_missing_price():
    """Solo el nombre sin precio → ValueError."""
    with pytest.raises(ValueError):
        parse_price_input("tomate")


def test_parse_price_invalid_number():
    """Precio no numérico → ValueError."""
    with pytest.raises(ValueError):
        parse_price_input("tomate abc")


# ─────────────────────────────── parse_pantry_input ───────────────────────────

def test_parse_pantry_basic():
    """arroz 2 kg → ('arroz', 2.0, 'kg')."""
    name, qty, unit = parse_pantry_input("arroz 2 kg")
    assert name == "arroz"
    assert qty == 2.0
    assert unit == "kg"


def test_parse_pantry_missing_unit():
    """arroz 2 → ValueError (falta la unidad)."""
    with pytest.raises(ValueError):
        parse_pantry_input("arroz 2")


def test_parse_pantry_multi_word_ingredient():
    """pechuga de pollo 0.5 kg → nombre multi-palabra."""
    name, qty, unit = parse_pantry_input("pechuga de pollo 0.5 kg")
    assert name == "pechuga de pollo"
    assert qty == 0.5
    assert unit == "kg"
