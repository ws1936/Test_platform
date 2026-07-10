"""add users.token_version for credential rotation

Revision ID: 0003_user_token_version
Revises: 0002_roles_and_fk
Create Date: 2026-07-10 16:52:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0003_user_token_version"
down_revision: Union[str, None] = "0002_roles_and_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ``token_version`` to users for invalidating old JWTs."""
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Remove ``token_version`` from users."""
    op.drop_column("users", "token_version")