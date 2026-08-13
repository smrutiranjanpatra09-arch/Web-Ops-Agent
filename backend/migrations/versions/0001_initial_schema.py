"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

from backend.app.database.session import Base
from backend.app import models  # noqa: F401 - registers all model tables on Base.metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Tables/columns added by later migrations (0002+). Base.metadata reflects the
# CURRENT model state, not the schema as it existed when 0001 was written, so
# anything a later migration is responsible for must be excluded here or that
# migration fails with "already exists" on a genuinely fresh database - this
# bit us for real: 0003 (password_hash) and 0004 (run_summaries) were both
# already being silently created by this create_all() before those migrations
# ever ran, which only stayed hidden because no environment had run 0001 fresh
# against today's models until a clean-DB hardening pass exercised it.
_TABLES_ADDED_LATER = {"run_summaries", "model_invocations", "chat_sessions", "chat_messages"}


def upgrade() -> None:
    # No live Postgres available to autogenerate against in this environment;
    # this migration applies the full model metadata directly rather than
    # hand-transcribed DDL, so it stays in lockstep with backend/app/models/.
    bind = op.get_bind()
    tables = [
        t for name, t in Base.metadata.tables.items()
        if name not in _TABLES_ADDED_LATER
    ]
    Base.metadata.create_all(bind=bind, tables=tables)
    # users.password_hash belongs to migration 0003 - drop it here so 0003's
    # ADD COLUMN remains valid on a fresh database.
    op.drop_column("users", "password_hash")
    # runs.archived/archived_at/archived_by and evidence.artifact_purged belong
    # to migration 0006 - drop them here for the same reason.
    op.drop_column("runs", "archived_by")
    op.drop_column("runs", "archived_at")
    op.drop_column("runs", "archived")
    op.drop_column("evidence", "artifact_purged")


def downgrade() -> None:
    bind = op.get_bind()
    tables = [
        t for name, t in Base.metadata.tables.items()
        if name not in _TABLES_ADDED_LATER
    ]
    Base.metadata.drop_all(bind=bind, tables=tables)
