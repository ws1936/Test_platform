"""Environment domain model for F005 — API testing environments.

Mirrors the canonical schema defined in ``docs/02-design/DATABASE.md``
§3.4. An environment belongs to an :class:`ApiProject` and supplies the
``base_url``, common request ``headers`` and ``variables`` used when
executing test cases.

Field summary (DATABASE.md §3.4)
--------------------------------

- ``id``: UUID primary key.
- ``project_id``: UUID FK -> ``api_projects.id`` (constraint added in
  migration ``0005_api_environments``).
- ``name``: environment name (VARCHAR(50), unique within a project).
- ``base_url``: base URL of the API under test (VARCHAR(500)).
- ``headers``: JSON object of common request headers (nullable).
- ``variables``: JSON object of environment variables (nullable).
- ``is_default``: whether this environment is the project's default.
- ``created_at`` / ``updated_at``: mandatory timestamps.

Implementation notes
--------------------

- The cross-table FK (``project_id`` → ``api_projects.id``) is **not**
  declared at the ORM level; it is created inside the Alembic
  migration. This matches the convention used by
  ``ApiProject.owner_id`` and keeps this module free of cross-domain
  imports.
- ``headers`` / ``variables`` use SQLAlchemy's portable ``JSON`` type
  so the same model works against PostgreSQL (rendered as JSON) and
  SQLite (rendered as TEXT). The application only stores
  string→primitive mappings in these columns, so JSON semantics are
  sufficient for the MVP — JSONB-specific queries are not used yet.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class ApiEnvironment(Base):
    """API testing environment entity (F005).

    See ``docs/02-design/DATABASE.md`` §3.4 and
    ``docs/02-design/MODULE.md`` §5 for the business rules this entity
    must enforce (unique name per project, at most one default
    environment per project).
    """

    __tablename__ = "api_environments"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    # FK to api_projects.id — the constraint is added by Alembic
    # migration ``0005_api_environments`` to keep this model
    # dependency-free (same style as ``ApiProject.owner_id``).
    project_id: Mapped[UUID] = mapped_column(
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    base_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    headers: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    variables: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    # ``is_default`` defaults to ``False`` both at the Python and SQL
    # level so an environment that is created without the flag is
    # never automatically promoted to the project default.
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ApiEnvironment(id={self.id}, project_id={self.project_id}, "
            f"name={self.name!r})>"
        )
