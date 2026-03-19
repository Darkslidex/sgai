"""Modelos ORM de SQLAlchemy.

Importar aquí todos los modelos para que Alembic los detecte en autogenerate.
"""

from app.database import Base  # noqa: F401 — re-export para alembic

# Los modelos se agregan en fases posteriores, ej:
# from app.adapters.persistence.food import FoodModel
