"""add api_projects table for F004

Revision ID: 0004_api_projects
Revises: 0003_user_token_version
Create Date: 2026-07-13 13:43:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


# revision identifiers, used by Alembic.
revision: str = "0004_api_projects"
down_revision: Union[str, None] = "0003_user_token_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create api_projects table with FK to users and owner_id index.

    Schema mirrors ``docs/02-design/DATABASE.md`` §3.3. ``owner_id`` uses
    ON DELETE RESTRICT (rather than SET NULL) because ``owner_id`` is NOT
    NULL — every project must have an owner and we must not silently
    orphan projects when a user record is removed.

    Implementation notes
    --------------------
    * ``UUID`` is declared with a SQLite ``CHAR(32)`` variant so the column
      renders as ``UUID`` on PostgreSQL and ``CHAR(32)`` on SQLite (the
      same shape used by ``users.id`` / ``roles.id``).
    * The FK is declared inline via ``ForeignKeyConstraint`` rather than
      ``op.create_foreign_key`` because SQLite does not support
      ``ALTER TABLE ADD CONSTRAINT``. Declaring it inside
      ``create_table`` keeps the migration dialect-portable.
    * ``server_default`` uses ``sa.func.now()`` rather than
      ``sa.text("now()")`` because SQLite has no ``now()`` function.
      ``func.now()`` is rendered as ``CURRENT_TIMESTAMP`` on SQLite and
      ``now()`` on PostgreSQL, matching ``users.created_at``.
    """
    op.create_table(
        "api_projects",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "owner_id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_api_projects_owner_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_projects"),
    )
    op.create_index(
        "idx_api_projects_owner_id",
        "api_projects",
        ["owner_id"],
    )


def downgrade() -> None:
    """Drop api_projects table and its index."""
    op.drop_index("idx_api_projects_owner_id", table_name="api_projects")
    op.drop_table("api_projects")