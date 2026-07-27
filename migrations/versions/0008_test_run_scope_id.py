"""persist test run scope_id for accurate replay

Revision ID: 0008_test_run_scope_id
Revises: 0007_api_test_runs_and_results
Create Date: 2026-07-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0008_test_run_scope_id"
down_revision: Union[str, None] = "0007_api_test_runs_and_results"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "api_test_runs",
        sa.Column(
            "scope_id",
            PG_UUID(as_uuid=True).with_variant(sa.CHAR(32), "sqlite"),
            nullable=True,
        ),
    )
    # Existing project-scope runs can be reconstructed from project_id.
    op.execute(
        "UPDATE api_test_runs SET scope_id = project_id "
        "WHERE scope = 'project' AND scope_id IS NULL"
    )
    op.create_index(
        "idx_api_test_runs_scope_id", "api_test_runs", ["scope_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_api_test_runs_scope_id", table_name="api_test_runs")
    op.drop_column("api_test_runs", "scope_id")
