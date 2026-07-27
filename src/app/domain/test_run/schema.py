"""Pydantic schemas for F010 test runs and test results.

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

F011 extensions
--------------
The report layer (F011) extends the F010 surface without changing
wire compatibility — every F010 field stays the same; the F011
aggregations live in dedicated schemas (see the bottom of the file)
and the two ``*computed*`` fields added to :class:`TestRunResponse`
(``pass_rate`` and ``elapsed_seconds``) are ``None`` until F010
finalises ``started_at`` / ``finished_at`` for a given run.
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


# === Response schemas (F010 baseline) ===


class TestRunResponse(BaseModel):
    """Detail response for a single test run.

    The two F011 *computed* fields live at the bottom of the
    declaration so the F010 field order is preserved. ``pass_rate``
    and ``elapsed_seconds`` are populated by the service layer
    (never persisted) so the model stays close to the DB schema.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    environment_id: UUID
    name: str
    scope: str
    scope_id: Optional[UUID] = None
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

    # === F011 computed fields (never persisted) ======================
    # ``pass_rate`` is ``passed / total`` rounded to 4 decimals; it
    # is ``None`` while the run is in flight (``status != "finished"``)
    # or when ``total == 0`` so the UI never displays a NaN.
    # ``elapsed_seconds`` is ``(finished_at - started_at).total_seconds()``;
    # also ``None`` until ``finished_at`` is set.
    pass_rate: Optional[float] = None
    elapsed_seconds: Optional[float] = None


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


# === F011 report schemas ====================================================


class TestRunSummaryResponse(BaseModel):
    """Single-run summary used by ``GET /runs/{run_id}/summary``.

    Mirrors :class:`TestRunResponse` plus an ``id`` alias (``run_id``)
    so the UI can render this without a second lookup. ``pass_rate``
    and ``elapsed_seconds`` are always populated (or ``None`` if the
    underlying run has not finished yet).
    """

    model_config = ConfigDict(from_attributes=True)

    run_id: UUID
    name: str
    scope: str
    scope_id: Optional[UUID] = None
    status: str
    total: int
    passed: int
    failed: int
    skipped: int
    error: int
    pass_rate: Optional[float] = None
    elapsed_seconds: Optional[float] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    environment_id: UUID


class ProjectRunsSummaryResponse(BaseModel):
    """Project-level roll-up used by ``GET /projects/{pid}/runs/summary``.

    Carries two flavours of stats:

    * ``total_runs`` / ``last_run_at`` — how many runs the project has
      ever executed and when the last one finished.
    * ``total_cases`` / ``total_passed`` / ``total_failed`` /
      ``total_error`` / ``overall_pass_rate`` — the sum of every
      result row in the project, used to render a project-level
      pass-rate gauge.
    * ``recent_runs`` — the most recent ``recent_limit`` runs, in
      newest-first order, so the UI can render a sparkline or a
      "last 10 runs" table.
    """

    project_id: UUID
    total_runs: int
    total_cases: int
    total_passed: int
    total_failed: int
    total_error: int
    overall_pass_rate: Optional[float] = None
    last_run_at: Optional[datetime] = None
    recent_runs: list[TestRunSummaryResponse]
    recent_limit: int = 10


class TestResultFailureItem(BaseModel):
    """One failed assertion extracted from a :class:`TestResult`.

    The original ``assertions_snapshot`` is a list of
    :class:`AssertionResult` payloads (see F009). The failure endpoint
    flattens that into one item per ``passed=False`` assertion so the
    report UI can render a clean failure list without re-parsing JSON.
    """

    result_id: UUID
    run_id: UUID
    test_case_id: UUID
    case_name: str
    case_method: str
    case_path: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    # The single failing assertion (extracted from assertions_snapshot).
    failure_index: int = Field(
        ..., description="0-based index inside the result's assertions_snapshot"
    )
    assertion_type: str
    assertion_operator: str
    expected: Any = None
    actual: Any = None
    message: str

    # Engine-level error (e.g. timeout / connect error) — set when the
    # whole result is ``status="error"`` rather than ``status="failed"``.
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class TestResultFailureListResponse(BaseModel):
    """Response for ``GET /runs/{run_id}/failures``."""

    run_id: UUID
    total_failures: int
    items: list[TestResultFailureItem]