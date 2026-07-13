"""Project domain model."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class ApiProject(Base):
    """API testing project entity model.

    A project is the boundary that owns environments, collections,
    test cases and test runs. See ``docs/02-design/DATABASE.md`` §3.3
    for the canonical schema definition.

    Field summary (DATABASE.md §3.3):

    - ``id``: UUID primary key.
    - ``name``: project name (VARCHAR(100)).
    - ``description``: optional description (TEXT).
    - ``owner_id``: FK -> users.id (constraint added in migration 0004).
    - ``created_at`` / ``updated_at``: mandatory timestamps.
    """

    __tablename__ = "api_projects"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    # FK to users.id. The actual foreign key constraint is created in
    # migration 0004 to keep this model free of cross-module imports,
    # matching the style used by ``User.role_id``.
    owner_id: Mapped[UUID] = mapped_column(
        nullable=False,
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
        return f"<ApiProject(id={self.id}, name={self.name})>"