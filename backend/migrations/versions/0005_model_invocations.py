"""add model_invocations table for LLM call audit trail

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_invocations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("chat_session_id", sa.String(), nullable=True),
        sa.Column("node", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("prompt_summary", sa.Text(), nullable=True),
        sa.Column("input_ref_ids", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("tokens_prompt", sa.Integer(), nullable=True),
        sa.Column("tokens_completion", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("fallback_triggered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_model_invocations_run_id", "model_invocations", ["run_id"])
    op.create_index("ix_model_invocations_created_at", "model_invocations", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_model_invocations_created_at", table_name="model_invocations")
    op.drop_index("ix_model_invocations_run_id", table_name="model_invocations")
    op.drop_table("model_invocations")
