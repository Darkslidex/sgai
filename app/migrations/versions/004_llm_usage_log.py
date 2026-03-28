"""Agregar tabla llm_usage_log para auditoría de uso de LLMs.

Revision ID: 004_llm_usage_log
Revises: 003_meal_logs
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa

revision = "004_llm_usage_log"
down_revision = "003_meal_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_usage_log_timestamp", "llm_usage_log", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_log_timestamp", table_name="llm_usage_log")
    op.drop_table("llm_usage_log")
