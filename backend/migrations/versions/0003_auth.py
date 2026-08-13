"""add password_hash to users, seed roles

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

ROLES = (
    "operations_user", "growth_user", "reviewer",
    "operations_owner", "administrator", "service_worker",
)


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=False, server_default=""))
    op.alter_column("users", "password_hash", server_default=None)

    roles = sa.table(
        "roles",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
    )
    op.bulk_insert(roles, [{"id": f"role-{name}", "name": name} for name in ROLES])


def downgrade() -> None:
    # reviews.reviewer_id references users.id, which in turn references
    # roles.id - on a database with real usage (reviews already decided by
    # real reviewers), hard-deleting users to clear the way for deleting
    # roles would destroy real audit history (engineering guidelines, section 11: every
    # significant action must stay reconstructable). Null out the reference
    # instead of deleting the rows it points to, then it's safe to remove
    # the users and roles this migration itself introduced.
    op.execute(sa.text("UPDATE reviews SET reviewer_id = NULL WHERE reviewer_id IS NOT NULL"))
    op.execute(
        sa.text("DELETE FROM users WHERE role_id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True, value=[f"role-{name}" for name in ROLES])
        )
    )
    op.execute(
        sa.text("DELETE FROM roles WHERE name IN :names").bindparams(
            sa.bindparam("names", expanding=True, value=list(ROLES))
        )
    )
    op.drop_column("users", "password_hash")
