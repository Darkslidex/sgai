"""Crea tabla meal_logs para registro de consumo alimentario.

Revision ID: 003_meal_logs
Revises: 002_enable_pgtrgm
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa

revision = "003_meal_logs"
down_revision = "002_enable_pgtrgm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meal_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("raw_description", sa.Text(), nullable=False),
        sa.Column("items_json", sa.JSON(), nullable=False),
        sa.Column("total_calories_kcal", sa.Float(), nullable=False),
        sa.Column("total_protein_g", sa.Float(), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="text"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meal_logs_date", "meal_logs", ["date"])


def downgrade() -> None:
    op.drop_index("ix_meal_logs_date", table_name="meal_logs")
    op.drop_table("meal_logs")
