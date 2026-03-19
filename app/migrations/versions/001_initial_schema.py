"""Initial schema — 10 tables [ADR-008: max_storage_volume]

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_chat_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("activity_level", sa.String(20), nullable=False),
        sa.Column("goal", sa.String(20), nullable=False),
        sa.Column(
            "max_storage_volume",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="ADR-008: Límite de Capacidad Física por categoría de producto",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_profiles_telegram_chat_id", "user_profiles", ["telegram_chat_id"], unique=True)

    op.create_table(
        "health_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sleep_score", sa.Float(), nullable=True),
        sa.Column("stress_level", sa.Float(), nullable=True),
        sa.Column("hrv", sa.Float(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("mood", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_health_logs_date", "health_logs", ["date"])

    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("prep_time_minutes", sa.Integer(), nullable=False),
        sa.Column("is_batch_friendly", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reheatable_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("servings", sa.Integer(), nullable=False),
        sa.Column("calories_per_serving", sa.Float(), nullable=False),
        sa.Column("protein_per_serving", sa.Float(), nullable=False),
        sa.Column("carbs_per_serving", sa.Float(), nullable=False),
        sa.Column("fat_per_serving", sa.Float(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("storage_type", sa.String(20), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("protein_per_100g", sa.Float(), nullable=True),
        sa.Column("calories_per_100g", sa.Float(), nullable=True),
        sa.Column("avg_shelf_life_days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("price_ars", sa.Float(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("store", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_prices_ingredient_date", "market_prices", ["ingredient_id", "date"])

    op.create_table(
        "weekly_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("plan_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("shopping_list_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total_cost_ars", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("quantity_amount", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"]),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pantry_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("quantity_amount", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "optimization_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("optimization_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("optimization_logs")
    op.drop_table("pantry_items")
    op.drop_table("recipe_ingredients")
    op.drop_table("user_preferences")
    op.drop_table("weekly_plans")
    op.drop_index("ix_market_prices_ingredient_date", table_name="market_prices")
    op.drop_table("market_prices")
    op.drop_table("ingredients")
    op.drop_table("recipes")
    op.drop_index("ix_health_logs_date", table_name="health_logs")
    op.drop_table("health_logs")
    op.drop_index("ix_user_profiles_telegram_chat_id", table_name="user_profiles")
    op.drop_table("user_profiles")
