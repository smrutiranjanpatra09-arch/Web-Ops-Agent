"""add chat_sessions and chat_messages tables, FK model_invocations.chat_session_id

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("grounded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_type", sa.String(), nullable=True),
        sa.Column("evidence_refs", sa.Text(), nullable=True),
        sa.Column("model_invocation_id", sa.String(), sa.ForeignKey("model_invocations.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    op.create_foreign_key(
        "fk_model_invocations_chat_session_id",
        "model_invocations", "chat_sessions",
        ["chat_session_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_model_invocations_chat_session_id", "model_invocations", type_="foreignkey")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
