"""add roles table and FK users.role_id

Revision ID: 0002_roles_and_fk
Revises: 0001_initial_users
Create Date: 2026-07-09 18:45:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0002_roles_and_fk"
down_revision: Union[str, None] = "0001_initial_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create roles table and add FK users.role_id -> roles.id."""
    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("permissions", sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"), nullable=True),
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.create_foreign_key(
        "fk_users_role_id_roles",
        source_table="users",
        referent_table="roles",
        local_cols=["role_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drop FK and roles table."""
    op.drop_constraint("fk_users_role_id_roles", "users", type_="foreignkey")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
