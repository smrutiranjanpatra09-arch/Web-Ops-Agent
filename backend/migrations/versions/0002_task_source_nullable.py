"""make task_sources.source_id nullable

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("task_sources", "source_id", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column("task_sources", "source_id", existing_type=sa.String(), nullable=False)
