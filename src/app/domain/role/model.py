"""Role domain model."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class Role(Base):
    """Role entity model.

    A role groups a set of permissions (stored as JSON list of strings).
    Users can be assigned to a single role via users.role_id.
    """

    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    # JSONB is preferred on PostgreSQL; falls back to JSON on SQLite for tests
    permissions: Mapped[Optional[list]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    is_system: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="System roles cannot be deleted",
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
        return f"<Role(id={self.id}, name={self.name})>"
