"""Database models for F010 — ``api_test_runs`` and ``api_test_results``.

A ``ApiTestRun`` represents one execution batch (PRD §5.7: "保存执行
批次"). Each batch produces one or more ``ApiTestResult`` rows — one
per test case that was attempted.

Schema mirrors the columns declared in
``migrations/versions/0007_api_test_runs_and_results.py``. The migration
is the source of truth for indexes / constraints; the ORM model only
declares columns and a few application-level indexes that aid common
queries.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class ApiTestRun(Base):
    """A single execution batch. F010.

    One row is created when the user triggers a run. Status transitions:

    * ``pending``   — just created, before the runner has touched it
    * ``running``   — at least one case has started executing
    * ``finished``  — all cases finished (success or failure)
    * ``failed``    — the runner itself crashed (uncaught exception)
    * ``canceled``  — explicit user cancel (reserved for F014+)

    Counters (``total`` / ``passed`` / ``failed`` / ``skipped`` /
    ``error``) are populated as each case finishes; ``finished_at``
    is set when the batch is sealed.
    """

    __tablename__ = "api_test_runs"
    __table_args__ = (
        Index("idx_api_test_runs_project_id", "project_id"),
        Index("idx_api_test_runs_environment_id", "environment_id"),
        Index("idx_api_test_runs_scope_id", "scope_id"),
        Index("idx_api_test_runs_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    environment_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_environments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    # Original Case/Suite/Project target. Nullable only for legacy rows that
    # predate migration 0008 and cannot be reconstructed safely.
    scope_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    triggered_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
            f"<ApiTestRun(id={self.id}, project_id={self.project_id}, "
            f"scope={self.scope!r}, status={self.status!r})>"
        )


class ApiTestResult(Base):
    """One test case execution result inside a ``ApiTestRun``. F010.

    Captures the request/response snapshot at execution time so the
    report (F011) can render the run later without needing the
    environment or case to still exist.

    Sensitive headers (``Authorization`` / ``Cookie`` / ``Set-Cookie``
    / ``X-Auth-*`` / ``X-API-Key``) are stripped *before* this row is
    persisted — see :func:`app.domain.test_engine.runner._sanitize_headers`.
    """

    __tablename__ = "api_test_results"
    __table_args__ = (
        Index("idx_api_test_results_run_id", "run_id"),
        Index("idx_api_test_results_test_case_id", "test_case_id"),
        Index("idx_api_test_results_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_test_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    test_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_test_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    case_name: Mapped[str] = mapped_column(String(200), nullable=False)
    case_method: Mapped[str] = mapped_column(String(10), nullable=False)
    case_path: Mapped[str] = mapped_column(String(500), nullable=False)
    environment_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_environments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    request_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    response_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    elapsed_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    assertions_snapshot: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSON, nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ApiTestResult(id={self.id}, case={self.case_name!r}, "
            f"status={self.status!r})>"
        )