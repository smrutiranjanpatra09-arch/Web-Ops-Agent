"""add run_summaries table for persisted AI completion narratives

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_summaries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.id"), nullable=False, unique=True),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("key_changes", sa.Text(), nullable=True),
        sa.Column("recommended_owner", sa.String(), nullable=True),
        sa.Column("confidence_note", sa.Text(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("generated_by", sa.String(), nullable=False, server_default="deterministic"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("run_summaries")
