"""HTTP endpoints for F010 test run management.

Endpoint summary (matches ``docs/03-api/API_GUIDE.md`` §3.7 + §3.8):

* ``POST   /projects/{project_id}/runs``              — create + execute
* ``GET    /projects/{project_id}/runs``              — list project runs
* ``GET    /runs/{run_id}``                           — run detail
* ``GET    /runs/{run_id}/results``                   — list results
* ``GET    /results/{result_id}``                     — single result
* ``POST   /test-cases/{case_id}/run``                — single-case run

Authorization (project owner / superuser) is enforced inside the
service layer; the router only handles HTTP concerns.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import get_current_user, get_test_run_service
from app.domain.test_run.schema import (
    TestResultListResponse,
    TestResultResponse,
    TestRunCreateRequest,
    TestRunListResponse,
    TestRunResponse,
)
from app.domain.test_run.service import TestRunService
from app.domain.user.model import User


# Three routers so the URL prefixes stay unambiguous (mirrors the
# pattern used by F005 / F007).
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
)
async def list_project_runs(
    project_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> TestRunListResponse:
    return await test_run_service.list_project_runs(
        project_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


# === Run-scoped endpoints (detail + results) ==============================


@run_resource_router.get(
    "/{run_id}",
    response_model=TestRunResponse,
    summary="Get test run detail",
)
async def get_run(
    run_id: UUID,
    test_run_service: TestRunService = Depends(get_test_run_service),
    current_user: User = Depends(get_current_user),
) -> TestRunResponse:
    run = await test_run_service.get_run(run_id, current_user=current_user)
    return TestRunResponse.model_validate(run)


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
    result = await test_run_service.get_result(
        result_id, current_user=current_user
    )
    return TestResultResponse.model_validate(result)


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