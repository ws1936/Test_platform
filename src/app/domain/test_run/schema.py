"""Pydantic schemas for F010 — test runs and test results.

Security note
-------------
``TestRunCreateRequest`` uses ``extra="forbid"`` so unknown fields are
rejected with 422 instead of being silently dropped. This prevents
clients from injecting fields like ``project_id``, ``run_id`` or
``status`` that the API contract does not declare.

Field mapping
-------------
* ``scope`` is constrained to ``Literal["case", "collection", "project"]``.
  ``scope_id`` is a UUID whose meaning depends on the scope (a case
  id, a suite id, or — for ``project`` — the project id itself, which
  is implied by the URL).
* ``triggered_by`` is exposed as a UUID on the wire; it is never
  accepted from the request body (the caller is the current user).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# === Constants ===

RunScope = Literal["case", "collection", "project"]
RunStatus = Literal[
    "pending", "running", "finished", "failed", "canceled"
]
ResultStatus = Literal["passed", "failed", "skipped", "error"]


# === Request schemas ===


class TestRunCreateRequest(BaseModel):
    """Create + execute a test run synchronously.

    ``scope_id`` semantics:

    * ``scope="case"``       → ``scope_id`` is a ``test_case_id``
    * ``scope="collection"`` → ``scope_id`` is a ``suite_id``
    * ``scope="project"``    → ``scope_id`` is ignored (the project
      is taken from the URL); we accept the field for API symmetry.
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="批次名称，可选；为空时自动生成 'Run @ {ISO timestamp}'",
    )
    environment_id: UUID = Field(..., description="执行使用的环境 ID")
    scope: RunScope = Field(..., description="执行范围")
    scope_id: UUID = Field(
        ...,
        description="范围 ID；按 scope 解释为 case_id / suite_id / project_id",
    )


# === Response schemas ===


class TestRunResponse(BaseModel):
    """Detail response for a single test run."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    environment_id: UUID
    name: str
    scope: str
    status: str
    total: int
    passed: int
    failed: int
    skipped: int
    error: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    triggered_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class TestRunListResponse(BaseModel):
    """Project-scoped list of runs (newest first)."""

    items: list[TestRunResponse]
    total: int


class TestResultResponse(BaseModel):
    """Detail response for a single case execution result."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    test_case_id: UUID
    case_name: str
    case_method: str
    case_path: str
    environment_id: UUID
    status: str
    request_snapshot: Optional[dict[str, Any]] = None
    response_snapshot: Optional[dict[str, Any]] = None
    elapsed_ms: Optional[int] = None
    assertions_snapshot: Optional[list[dict[str, Any]]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime


class TestResultListResponse(BaseModel):
    """Run-scoped list of case execution results (insertion order)."""

    items: list[TestResultResponse]
    total: int