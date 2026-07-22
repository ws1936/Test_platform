"""HTTP endpoints for F010 test run management + F011 report aggregations.

Endpoint summary (matches ``docs/03-api/API_GUIDE.md`` §3.7 + §3.8):

F010 — execution surface
* ``POST   /projects/{project_id}/runs``              — create + execute
* ``GET    /projects/{project_id}/runs``              — list project runs
* ``GET    /runs/{run_id}``                           — run detail
* ``GET    /runs/{run_id}/results``                   — list results
* ``GET    /results/{result_id}``                     — single result
* ``POST   /test-cases/{case_id}/run``                — single-case run

F011 — report surface
* ``GET    /projects/{project_id}/runs/summary``      — project-level roll-up
* ``GET    /runs/{run_id}/summary``                   — single-run roll-up
* ``GET    /runs/{run_id}/failures``                  — flattened failure list

Authorization (project owner / superuser) is enforced inside the
service layer; the router only handles HTTP concerns.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.common.dependencies import get_current_user, get_test_run_service
from app.domain.test_run.schema import (
    ProjectRunsSummaryResponse,
    RunStatus,
    TestResultFailureListResponse,
    TestResultListResponse,
    TestResultResponse,
    TestRunCreateRequest,
    TestRunListResponse,
    TestRunResponse,
    TestRunSummaryResponse,
)
from app.domain.test_run.service import TestRunService
from app.domain.user.model import User


# Three routers so the URL prefixes stay unambiguous (mirrors the
# pattern used by F005 / F007). F011 added ``run_resource_router``-prefixed
# ``/summary`` and ``/failures`` endpoints below.
run_router = APIRouter(prefix="/projects", tags=["TestRun"])
case_router = APIRouter(prefix="/test-cases", tags=["TestRun"])
run_resource_router = APIRouter(prefix="/runs", tags=["TestRun"])
result_router = APIRouter(prefix="/results", tags=["TestRun"])


# === Project-scoped endpoints (create + list) ==============================


@run_router.post(
    "/{project_id}/runs",
    response_model=TestRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and execute a test run",
    description=(
        "Create a new test run under the given project and execute it "
        "synchronously. The response includes the final state of the "
        "run — counters, status, and timestamps — because MVP runs "
        "are synchronous (AI_RULES §4.4: no Celery / no background "
        "workers). For long runs in the future, F014 will introduce "
        "async execution."
    ),
    responses={
        201: {"description": "Run created and finished"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Project / environment / suite / case not found"},
        422: {"description": "Validation error or empty scope"},
    },
)
async def create_run(
    project_id: UUID,
    request: TestRunCreateRequest,
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> TestRunResponse:
    return await test_run_service.create_run(
        project_id, request, current_user=current_user
    )


@run_router.get(
    "/{project_id}/runs",
    response_model=TestRunListResponse,
    summary="List runs of a project (newest first)",
    description=(
        "F011 added an optional ``?status=`` query parameter so the "
        "history view can show only the failed runs (or any other "
        "single status)."
    ),
)
async def list_project_runs(
    project_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[RunStatus] = Query(
        default=None,
        alias="status",
        description=(
            "F011 filter — pass ``failed`` to show only the runs "
            "that finished with at least one failure/error. Omit "
            "to keep the F010 unfiltered behaviour."
        ),
    ),
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> TestRunListResponse:
    return await test_run_service.list_project_runs(
        project_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
        status=status_filter,
    )


# === F011: project-level roll-up ==========================================


@run_router.get(
    "/{project_id}/runs/summary",
    response_model=ProjectRunsSummaryResponse,
    summary="Project-level runs roll-up (F011 report)",
    description=(
        "Aggregates every run/result in the project so the report UI "
        "can render a single pass-rate gauge + a ``recent_runs`` "
        "table (default last 10). All counts are SQL aggregates; no "
        "Python-side iteration."
    ),
    responses={
        200: {"description": "Aggregated project summary"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Project not found"},
    },
)
async def summarize_project_runs(
    project_id: UUID,
    recent_limit: int = Query(
        default=10, ge=1, le=50,
        description="How many recent runs to include in ``recent_runs``",
    ),
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> ProjectRunsSummaryResponse:
    return await test_run_service.summarize_project_runs(
        project_id,
        current_user=current_user,
        recent_limit=recent_limit,
    )


# === Run-scoped endpoints (detail + results) ==============================


@run_resource_router.get(
    "/{run_id}",
    response_model=TestRunResponse,
    summary="Get test run detail",
    description=(
        "Returns the full run state. F011 added two computed fields "
        "(``pass_rate`` and ``elapsed_seconds``) to the response so "
        "the UI does not need a second round-trip to the summary "
        "endpoint."
    ),
)
async def get_run(
    run_id: UUID,
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> TestRunResponse:
    return await test_run_service.get_run(run_id, current_user=current_user)


@run_resource_router.get(
    "/{run_id}/results",
    response_model=TestResultListResponse,
    summary="List test results of a run",
)
async def list_run_results(
    run_id: UUID,
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> TestResultListResponse:
    return await test_run_service.list_run_results(
        run_id, current_user=current_user
    )


# === F011: single-run summary + failure list =============================


@run_resource_router.get(
    "/{run_id}/summary",
    response_model=TestRunSummaryResponse,
    summary="Single-run summary (F011 report)",
    description=(
        "Returns the run's counters + ``pass_rate`` + "
        "``elapsed_seconds`` in one shot. Mirrors :class:`TestRunResponse` "
        "but with a ``run_id`` alias for UI convenience."
    ),
    responses={
        200: {"description": "Run summary"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Run not found"},
    },
)
async def summarize_run(
    run_id: UUID,
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> TestRunSummaryResponse:
    return await test_run_service.summarize_run(
        run_id, current_user=current_user
    )


@run_resource_router.get(
    "/{run_id}/export",
    summary="Export a run report (F015)",
    description=(
        "F015：导出单次 Run 的完整报告。支持两种格式：``json``（默认）"
        "和 ``html``（自带简易模板，无需 jinja2）。响应体是纯文本，"
        "前端可直接下载。"
    ),
    responses={
        200: {"description": "Exported report (Content-Type 视 format 而定)"},
        400: {"description": "Invalid format"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Run not found"},
    },
)
async def export_run(
    run_id: UUID,
    format: str = Query(
        default="json",
        pattern="^(json|html)$",
        description="导出格式：json 或 html",
    ),
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> Response:
    content, media_type, filename = await test_run_service.export_run(
        run_id, format, current_user=current_user
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )




@run_resource_router.get(
    "/{run_id}/failures",
    response_model=TestResultFailureListResponse,
    summary="Flattened failure list of a run (F011 report)",
    description=(
        "Walks every result in the run, flattens their "
        "``assertions_snapshot`` JSON to one item per failed "
        "assertion, and also surfaces engine errors (timeout / "
        "connect) as ``status=\"execution\"`` items. The response is "
        "empty when the run passed everything."
    ),
    responses={
        200: {"description": "Failure list (possibly empty)"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Run not found"},
    },
)
async def list_run_failures(
    run_id: UUID,
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> TestResultFailureListResponse:
    return await test_run_service.list_run_failures(
        run_id, current_user=current_user
    )


# === Result-scoped endpoint (single detail) ===============================


@result_router.get(
    "/{result_id}",
    response_model=TestResultResponse,
    summary="Get a single test result detail",
    description=(
        "Returns the full result row including the request and "
        "response snapshots and the assertions list. Bodies larger "
        "than 64 KiB are truncated; ``response_snapshot.body_truncated`` "
        "indicates this."
    ),
)
async def get_result(
    result_id: UUID,
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> TestResultResponse:
    return await test_run_service.get_result(
        result_id, current_user=current_user
    )


# === Single-case shortcut ================================================


@case_router.post(
    "/{case_id}/run",
    response_model=TestRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute a single test case",
    description=(
        "Convenience endpoint that wraps ``POST /projects/{pid}/runs`` "
        "with ``scope=\"case\"``. Internally a 1-case run is created "
        "and executed synchronously."
    ),
)
async def run_single_case(
    case_id: UUID,
    environment_id: UUID = Query(...),
    name: Optional[str] = Query(default=None),
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> TestRunResponse:
    return await test_run_service.run_test_case(
        case_id,
        environment_id,
        current_user=current_user,
        name=name,
    )