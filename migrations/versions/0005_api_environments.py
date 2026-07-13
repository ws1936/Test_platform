"""add api_environments table for F005

Revision ID: 0005_api_environments
Revises: 0004_api_projects
Create Date: 2026-07-13 17:18:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


# revision identifiers, used by Alembic.
revision: str = "0005_api_environments"
down_revision: Union[str, None] = "0004_api_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create api_environments table with FK to api_projects.

    Schema mirrors ``docs/02-design/DATABASE.md`` §3.4. The ``headers``
    and ``variables`` columns are declared as portable JSON so the
    same migration runs against PostgreSQL (JSON) and SQLite (TEXT,
    used by the pytest suite).

    Implementation notes
    --------------------
    * ``UUID`` is declared with a SQLite ``CHAR(32)`` variant so the
      column renders as ``UUID`` on PostgreSQL and ``CHAR(32)`` on
      SQLite (same shape used by ``users.id`` / ``api_projects.id``).
    * The FK is declared inline via ``ForeignKeyConstraint`` rather
      than ``op.create_foreign_key`` because SQLite does not support
      ``ALTER TABLE ADD CONSTRAINT``. Declaring it inside
      ``create_table`` keeps the migration dialect-portable.
    * ``is_default`` uses ``Boolean`` with a ``server_default`` of
      ``false``; SQLAlchemy renders this as ``DEFAULT FALSE`` on
      PostgreSQL and ``DEFAULT 0`` on SQLite.
    * In addition to the plain indexes declared in DATABASE.md §4, a
      **partial** unique index is added on PostgreSQL so the database
      itself guarantees "at most one default environment per
      project" (MODULE.md §5). SQLite does not support partial
      indexes, so we add a regular index there instead and rely on
      the service layer (EnvironmentService) to keep the invariant
      inside a single transaction.
    """
    op.create_table(
        "api_environments",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=True),
        sa.Column("variables", sa.JSON(), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
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
            ["project_id"],
            ["api_projects.id"],
            name="fk_api_environments_project_id_api_projects",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_environments"),
        sa.UniqueConstraint(
            "project_id",
            "name",
            name="uq_api_environments_project_name",
        ),
    )
    op.create_index(
        "idx_api_environments_project_id",
        "api_environments",
        ["project_id"],
    )

    # Partial unique index — PostgreSQL only. SQLite ignores it but
    # the pytest suite relies on the in-transaction demotion in
    # ``EnvironmentService`` to keep the invariant.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE UNIQUE INDEX uq_api_environments_one_default_per_project "
            "ON api_environments (project_id) WHERE is_default = true"
        )


def downgrade() -> None:
    """Drop api_environments table and its indexes."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS uq_api_environments_one_default_per_project")
    op.drop_index("idx_api_environments_project_id", table_name="api_environments")
    op.drop_table("api_environments")
