"""Database models for F006 suite management."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class ApiSuite(Base):
    """A named, project-scoped collection of API test cases."""

    __tablename__ = "api_suites"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_api_suites_project_name"),
        Index("idx_api_suites_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
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
            f"<ApiSuite(id={self.id}, project_id={self.project_id}, "
            f"name={self.name!r})>"
        )


class ApiSuiteCase(Base):
    """Ordered many-to-many association between a suite and a test case."""

    __tablename__ = "api_suite_cases"
    __table_args__ = (
        UniqueConstraint(
            "suite_id",
            "test_case_id",
            name="uq_api_suite_cases_suite_testcase",
        ),
        Index("idx_api_suite_cases_suite_id", "suite_id"),
        Index("idx_api_suite_cases_test_case_id", "test_case_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    suite_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_suites.id", ondelete="CASCADE"),
        nullable=False,
    )
    test_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_test_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    # ``order`` is the public F006 term.  The compatibility property below
    # keeps older callers that used ``sort_order`` working.
    order: Mapped[int] = mapped_column(
        "order", Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @property
    def sort_order(self) -> int:
        """Backward-compatible alias for clients written before F006 settled."""
        return self.order

    @sort_order.setter
    def sort_order(self, value: int) -> None:
        self.order = value

    @property
    def case_id(self) -> UUID:
        """Concise alias used by some API clients."""
        return self.test_case_id

    def __repr__(self) -> str:
        return (
            f"<ApiSuiteCase(id={self.id}, suite_id={self.suite_id}, "
            f"test_case_id={self.test_case_id}, order={self.order})>"
        )
