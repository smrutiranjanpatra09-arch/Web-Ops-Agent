"""add run archival fields and evidence artifact_purged flag

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("runs", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("runs", sa.Column("archived_by", sa.String(), sa.ForeignKey("users.id"), nullable=True))
    op.create_index("ix_runs_archived", "runs", ["archived"])

    op.add_column(
        "evidence",
        sa.Column("artifact_purged", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("evidence", "artifact_purged")

    op.drop_index("ix_runs_archived", table_name="runs")
    op.drop_column("runs", "archived_by")
    op.drop_column("runs", "archived_at")
    op.drop_column("runs", "archived")
