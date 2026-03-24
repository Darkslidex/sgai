"""Habilita extensión pg_trgm para búsqueda fuzzy de ingredientes.

Revision ID: 002_enable_pgtrgm
Revises: 001_initial_schema
Create Date: 2026-03-24
"""

from alembic import op

revision = "002_enable_pgtrgm"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
