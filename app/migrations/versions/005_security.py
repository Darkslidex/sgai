"""Agregar tabla ana_access_log para audit trail de accesos de Ana.

Revision ID: 005_security
Revises: 004_llm_usage_log
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa

revision = "005_security"
down_revision = "004_llm_usage_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ana_access_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("endpoint", sa.String(200), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ana_access_log_timestamp", "ana_access_log", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_ana_access_log_timestamp", table_name="ana_access_log")
    op.drop_table("ana_access_log")
