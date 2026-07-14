"""add api_test_runs and api_test_results tables for F010

Revision ID: 0007_api_test_runs_and_results
Revises: 0006_api_suites
Create Date: 2026-07-14 15:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


# revision identifiers, used by Alembic.
revision: str = "0007_api_test_runs_and_results"
down_revision: Union[str, None] = "0006_api_suites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ``api_test_runs`` and ``api_test_results`` for F010.

    Schema mirrors ARCHITECTURE.md §4.2 ("TestRun / TestResult 核心模块")
    and PRD §5.7/5.8 (保存执行批次和每条结果).

    Implementation notes
    --------------------
    * ``UUID`` is declared with a SQLite ``CHAR(32)`` variant so the
      column renders as ``UUID`` on PostgreSQL and ``CHAR(32)`` on
      SQLite (same shape used by every other table in the project).
    * FK constraints are declared inline so the migration stays
      dialect-portable (SQLite cannot ``ALTER TABLE ADD CONSTRAINT``).
    * ``scope`` and ``status`` are ``VARCHAR(20)`` + ``CHECK`` constraints
      — the application-level enums live in
      :mod:`app.domain.test_run.schema`.
    * Sensitive response headers (Authorization, Cookie, …) are *not*
      stored in ``response_snapshot``; the test_engine strips them
      before persistence.
    * ``api_test_results.request_snapshot`` / ``response_snapshot``
      are stored as ``JSON`` (portable across both dialects) and may
      be ``NULL`` when execution itself failed before a response was
      produced.
    """
    op.create_table(
        "api_test_runs",
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
        sa.Column(
            "environment_id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("pending"),
        ),
        sa.Column(
            "total",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "passed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "failed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "skipped",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "error",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "triggered_by",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=True,
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
            name="fk_api_test_runs_project_id_api_projects",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["api_environments.id"],
            name="fk_api_test_runs_environment_id_api_environments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by"],
            ["users.id"],
            name="fk_api_test_runs_triggered_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_test_runs"),
        sa.CheckConstraint(
            "scope IN ('case', 'collection', 'project')",
            name="ck_api_test_runs_scope",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'finished', 'failed', 'canceled')",
            name="ck_api_test_runs_status",
        ),
    )
    op.create_index(
        "idx_api_test_runs_project_id", "api_test_runs", ["project_id"]
    )
    op.create_index(
        "idx_api_test_runs_environment_id",
        "api_test_runs",
        ["environment_id"],
    )
    op.create_index(
        "idx_api_test_runs_status", "api_test_runs", ["status"]
    )

    op.create_table(
        "api_test_results",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "test_case_id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column("case_name", sa.String(length=200), nullable=False),
        sa.Column("case_method", sa.String(length=10), nullable=False),
        sa.Column("case_path", sa.String(length=500), nullable=False),
        sa.Column(
            "environment_id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("request_snapshot", sa.JSON(), nullable=True),
        sa.Column("response_snapshot", sa.JSON(), nullable=True),
        sa.Column("elapsed_ms", sa.Integer(), nullable=True),
        sa.Column("assertions_snapshot", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["api_test_runs.id"],
            name="fk_api_test_results_run_id_api_test_runs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["api_test_cases.id"],
            name="fk_api_test_results_test_case_id_api_test_cases",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id"],
            ["api_environments.id"],
            name="fk_api_test_results_environment_id_api_environments",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_test_results"),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'skipped', 'error')",
            name="ck_api_test_results_status",
        ),
    )
    op.create_index(
        "idx_api_test_results_run_id", "api_test_results", ["run_id"]
    )
    op.create_index(
        "idx_api_test_results_test_case_id",
        "api_test_results",
        ["test_case_id"],
    )
    op.create_index(
        "idx_api_test_results_status", "api_test_results", ["status"]
    )


def downgrade() -> None:
    """Reverse F010 — drop both tables and their indexes."""
    op.drop_index("idx_api_test_results_status", table_name="api_test_results")
    op.drop_index(
        "idx_api_test_results_test_case_id", table_name="api_test_results"
    )
    op.drop_index("idx_api_test_results_run_id", table_name="api_test_results")
    op.drop_table("api_test_results")
    op.drop_index("idx_api_test_runs_status", table_name="api_test_runs")
    op.drop_index(
        "idx_api_test_runs_environment_id", table_name="api_test_runs"
    )
    op.drop_index("idx_api_test_runs_project_id", table_name="api_test_runs")
    op.drop_table("api_test_runs")