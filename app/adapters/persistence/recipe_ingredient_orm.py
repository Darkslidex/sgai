"""Modelo ORM: recipe_ingredients (M:M entre recetas e ingredientes)."""

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecipeIngredientORM(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity_amount: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
