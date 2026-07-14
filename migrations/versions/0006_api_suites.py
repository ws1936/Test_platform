"""add api_suites and api_suite_cases tables for F006

Revision ID: 0006_api_suites
Revises: 0005_api_environments
Create Date: 2026-07-13 18:25:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


# revision identifiers, used by Alembic.
revision: str = "0006_api_suites"
down_revision: Union[str, None] = "0005_api_environments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create api_suites and api_suite_cases tables.

    Schema mirrors ``docs/02-design/DATABASE.md`` §3.5 (Collection →
    Suite per the F006 task brief) plus the new
    ``api_suite_cases`` association table that F007 will populate.

    Implementation notes
    --------------------
    * ``UUID`` is declared with a SQLite ``CHAR(32)`` variant so the
      column renders as ``UUID`` on PostgreSQL and ``CHAR(32)`` on
      SQLite (same shape used by users.id / api_projects.id /
      api_environments.id).
    * The FK from ``api_suites.project_id`` → ``api_projects.id`` is
      declared inline so the migration stays dialect-portable
      (SQLite cannot ``ALTER TABLE ADD CONSTRAINT``).
    * ``api_suite_cases.test_case_id`` does **not** carry a FK yet
      because ``api_test_cases`` will be introduced by the F007
      migration. The index on this column is still useful for the
      future "which suites contain this case?" lookup.
    * ``api_suite_cases`` uses ``ON DELETE CASCADE`` from both
      ``suite_id`` and (eventually) ``test_case_id`` so neither side
      can leave orphan rows behind.
    * ``(suite_id, test_case_id)`` carries a ``UNIQUE`` constraint so
      the service can treat "re-add the same case" as a no-op
      instead of producing duplicate rows.
    * The ``(project_id, name)`` uniqueness rule on ``api_suites``
      matches the convention used by ``api_environments`` so callers
      can rely on identical 409 semantics across modules.
    """
    op.create_table(
        "api_suites",
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
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
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
            name="fk_api_suites_project_id_api_projects",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_suites"),
        sa.UniqueConstraint(
            "project_id",
            "name",
            name="uq_api_suites_project_name",
        ),
    )
    op.create_index(
        "idx_api_suites_project_id",
        "api_suites",
        ["project_id"],
    )

    # F006 must validate that suite-case references exist even though the
    # full F007 CRUD API has not landed yet.  Create the canonical test-case
    # table now so associations can carry an actual foreign key.
    op.create_table(
        "api_test_cases",
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
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=True),
        sa.Column("query_params", sa.JSON(), nullable=True),
        sa.Column("body_type", sa.String(length=20), nullable=False),
        sa.Column("body", sa.JSON(), nullable=True),
        sa.Column("assertions", sa.JSON(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
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
            name="fk_api_test_cases_project_id_api_projects",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_test_cases"),
    )
    op.create_index("idx_api_test_cases_project_id", "api_test_cases", ["project_id"])
    op.create_index("idx_api_test_cases_status", "api_test_cases", ["status"])

    op.create_table(
        "api_suite_cases",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "suite_id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "test_case_id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
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
            ["suite_id"],
            ["api_suites.id"],
            name="fk_api_suite_cases_suite_id_api_suites",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["api_test_cases.id"],
            name="fk_api_suite_cases_test_case_id_api_test_cases",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_suite_cases"),
        sa.UniqueConstraint(
            "suite_id",
            "test_case_id",
            name="uq_api_suite_cases_suite_testcase",
        ),
    )
    op.create_index(
        "idx_api_suite_cases_suite_id",
        "api_suite_cases",
        ["suite_id"],
    )
    op.create_index(
        "idx_api_suite_cases_test_case_id",
        "api_suite_cases",
        ["test_case_id"],
    )


def downgrade() -> None:
    """Drop api_suite_cases and api_suites tables."""
    op.drop_index("idx_api_suite_cases_test_case_id", table_name="api_suite_cases")
    op.drop_index("idx_api_suite_cases_suite_id", table_name="api_suite_cases")
    op.drop_table("api_suite_cases")
    op.drop_index("idx_api_test_cases_status", table_name="api_test_cases")
    op.drop_index("idx_api_test_cases_project_id", table_name="api_test_cases")
    op.drop_table("api_test_cases")
    op.drop_index("idx_api_suites_project_id", table_name="api_suites")
    op.drop_table("api_suites")
