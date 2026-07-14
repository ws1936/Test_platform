"""Persistence model for API test cases.

The F006 suite module references test cases before the F007 HTTP API is
implemented.  Keeping the identity and core request fields in a real table
lets F006 enforce two important invariants now: a case must exist and it must
belong to the same project as the suite.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class ApiTestCase(Base):
    """API test-case entity shared by suites and the future F007 API."""

    __tablename__ = "api_test_cases"
    __table_args__ = (
        Index("idx_api_test_cases_project_id", "project_id"),
        Index("idx_api_test_cases_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    path: Mapped[str] = mapped_column(String(500), nullable=False, default="/")
    headers: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    query_params: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    body_type: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    body: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    assertions: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSON, nullable=True
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ApiTestCase(id={self.id}, project_id={self.project_id}, "
            f"name={self.name!r})>"
        )
