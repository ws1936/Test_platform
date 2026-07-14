"""Authenticated HTTP endpoints for F007 API test case management.

All endpoints require authentication. Authorization (project owner or
superuser) is enforced inside the service layer.

Endpoint summary (matches ``docs/03-api/API_GUIDE.md`` §3.7 plus a
project-scoped list):

* ``POST   /collections/{suite_id}/cases``              — create
* ``GET    /collections/{suite_id}/cases``              — list cases
                                                       attached to a
                                                       suite
* ``GET    /projects/{project_id}/test-cases``          — list every
                                                       test case of a
                                                       project
* ``GET    /test-cases/{case_id}``                      — detail
* ``PUT    /test-cases/{case_id}``                      — update
* ``DELETE /test-cases/{case_id}``                      — delete

Path choice rationale
--------------------
``/collections/{suite_id}/cases`` follows API_GUIDE §3.7. The
collection prefix is a stable API contract; internally a "collection"
is a ``suite`` row (F006), so the service resolves the suite first
and pins the new case to ``suite.project_id``.

``/projects/{project_id}/test-cases`` is an additional, project-
scoped list endpoint that F007 exposes so the UI can show cases that
are not yet attached to any suite.

``/test-cases/{case_id}`` is the resource-scoped detail / update /
delete surface so a case URL keeps working after the case is removed
from every suite.

Note on DELETE
--------------
``DELETE`` returns ``200 OK`` with a ``MessageResponse`` body rather
than ``204 No Content`` because FastAPI forbids any response model
on a 204 status code. This matches the convention used by
``environment_router.delete_environment`` /
``project_router.delete_project``.

Note on F010
------------
``POST /test-cases/{case_id}/run`` is **not** implemented in F007 —
execution is the responsibility of F010 (pytest / API execution).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import get_current_user, get_test_case_service
from app.domain.test_case.schema import (
    TestCaseCreateRequest,
    TestCaseListResponse,
    TestCaseResponse,
    TestCaseUpdateRequest,
)
from app.domain.test_case.service import TestCaseService
from app.domain.user.model import User
from app.domain.user.schema import MessageResponse


# Three separate routers so the URL prefixes stay unambiguous.  Using
# one router with overlapping prefixes makes OpenAPI generation less
# predictable and confuses FastAPI's matcher when one of the routes
# grows in the future.
collection_router = APIRouter(prefix="/collections", tags=["TestCase"])
project_router = APIRouter(prefix="/projects", tags=["TestCase"])
case_router = APIRouter(prefix="/test-cases", tags=["TestCase"])


# === Suite-scoped endpoints (create + list) ===


@collection_router.post(
    "/{suite_id}/cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a test case under a suite",
    description=(
        "Create a new API test case anchored to the given suite. "
        "Authorization: project owner or superuser. The case is "
        "stored against the suite's project; the suite's project "
        "is the only source of project_id the service will honour."
    ),
    responses={
        201: {"description": "Test case created"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Suite not found"},
        422: {"description": "Validation error"},
    },
)
async def create_test_case(
    suite_id: UUID,
    request: TestCaseCreateRequest,
    test_case_service: TestCaseService = Depends(get_test_case_service),
    current_user: User = Depends(get_current_user),
) -> TestCaseResponse:
    return await test_case_service.create_test_case(
        suite_id, request, current_user=current_user
    )


@collection_router.get(
    "/{suite_id}/cases",
    response_model=list[TestCaseResponse],
    status_code=status.HTTP_200_OK,
    summary="List test cases attached to a suite",
    description=(
        "Return every test case currently associated with the suite, "
        "in the same order they appear in the suite. Free-floating "
        "cases (not attached to any suite) are not returned here — "
        "use the project-scoped list for that view. Authorization: "
        "project owner or superuser."
    ),
    responses={
        200: {"description": "Test case list"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Suite not found"},
    },
)
async def list_suite_cases(
    suite_id: UUID,
    test_case_service: TestCaseService = Depends(get_test_case_service),
    current_user: User = Depends(get_current_user),
) -> list[TestCaseResponse]:
    return await test_case_service.list_suite_cases(
        suite_id, current_user=current_user
    )


# === Project-scoped endpoint (every case, including free-floating) ===


@project_router.get(
    "/{project_id}/test-cases",
    response_model=TestCaseListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all test cases of a project",
    description=(
        "Return every test case of a project, including free-floating "
        "cases that are not attached to any suite. Supports an "
        "optional ``search`` query parameter that filters by name. "
        "Authorization: project owner or superuser."
    ),
    responses={
        200: {"description": "Test case list"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Project not found"},
    },
)
async def list_project_cases(
    project_id: UUID,
    search: str | None = Query(
        default=None,
        description="按 name 模糊搜索（大小写不敏感）",
    ),
    test_case_service: TestCaseService = Depends(get_test_case_service),
    current_user: User = Depends(get_current_user),
) -> TestCaseListResponse:
    return await test_case_service.list_project_cases(
        project_id, current_user=current_user, search=search
    )


# === Test-case-scoped endpoints (detail / update / delete) ===


@case_router.get(
    "/{case_id}",
    response_model=TestCaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get test case detail",
    description=(
        "Return a single test case. Authorization: project owner or "
        "superuser. Non-owners get 403; missing cases return 404."
    ),
    responses={
        200: {"description": "Test case detail"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Test case not found"},
    },
)
async def get_test_case(
    case_id: UUID,
    test_case_service: TestCaseService = Depends(get_test_case_service),
    current_user: User = Depends(get_current_user),
) -> TestCaseResponse:
    case = await test_case_service.get_test_case(
        case_id, current_user=current_user
    )
    return test_case_service._to_response(case)


@case_router.put(
    "/{case_id}",
    response_model=TestCaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a test case",
    description=(
        "Partial update — only fields present in the payload are "
        "touched. ``extra`` fields are rejected with 422. "
        "Authorization: project owner or superuser."
    ),
    responses={
        200: {"description": "Updated"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Test case not found"},
        422: {"description": "Validation error"},
    },
)
async def update_test_case(
    case_id: UUID,
    request: TestCaseUpdateRequest,
    test_case_service: TestCaseService = Depends(get_test_case_service),
    current_user: User = Depends(get_current_user),
) -> TestCaseResponse:
    return await test_case_service.update_test_case(
        case_id, request, current_user=current_user
    )


@case_router.delete(
    "/{case_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a test case",
    description=(
        "Hard-delete a test case. Authorization: project owner or "
        "superuser. Suite associations on ``api_suite_cases`` are "
        "removed automatically via ``ON DELETE CASCADE``."
    ),
    responses={
        200: {"description": "Deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Test case not found"},
    },
)
async def delete_test_case(
    case_id: UUID,
    test_case_service: TestCaseService = Depends(get_test_case_service),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await test_case_service.delete_test_case(case_id, current_user=current_user)
    return MessageResponse(message="Test case deleted")