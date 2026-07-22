"""Authenticated HTTP endpoints for F006 suite management."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import get_current_user, get_suite_service
from app.common.exceptions import SuiteNotFoundException
from app.domain.suite.schema import (
    SuiteCaseResponse,
    SuiteCasesBulkCreate,
    SuiteCasesBulkResponse,
    SuiteCasesReorderRequest,
    SuiteCreateRequest,
    SuiteDetailResponse,
    SuiteListResponse,
    SuiteResponse,
    SuiteUpdateRequest,
)
from app.domain.suite.service import SuiteService
from app.domain.user.model import User
from app.domain.user.schema import MessageResponse

router = APIRouter(prefix="/projects/{project_id}/suites", tags=["Suite"])


async def _assert_path_scope(
    *,
    project_id: UUID,
    suite_id: UUID,
    suite_service: SuiteService,
    current_user: User,
) -> None:
    """Reject a valid suite nested beneath the wrong project URL.

    This check deliberately runs before every write so a mismatched path can
    never mutate a suite and then return 404 afterwards.
    """
    suite = await suite_service.get_suite(suite_id, current_user=current_user)
    if suite.project_id != project_id:
        raise SuiteNotFoundException()


@router.post("", response_model=SuiteResponse, status_code=status.HTTP_201_CREATED)
async def create_suite(
    project_id: UUID,
    request: SuiteCreateRequest,
    suite_service: SuiteService = Depends(get_suite_service),
    current_user: User = Depends(get_current_user),
) -> SuiteResponse:
    return await suite_service.create_suite(
        project_id, request, current_user=current_user
    )


@router.get("", response_model=SuiteListResponse)
async def list_suites(
    project_id: UUID,
    search: str | None = Query(default=None),
    suite_service: SuiteService = Depends(get_suite_service),
    current_user: User = Depends(get_current_user),
) -> SuiteListResponse:
    return await suite_service.list_suites(
        project_id, current_user=current_user, search=search
    )


@router.get("/{suite_id}", response_model=SuiteDetailResponse)
async def get_suite(
    project_id: UUID,
    suite_id: UUID,
    suite_service: SuiteService = Depends(get_suite_service),
    current_user: User = Depends(get_current_user),
) -> SuiteDetailResponse:
    await _assert_path_scope(
        project_id=project_id,
        suite_id=suite_id,
        suite_service=suite_service,
        current_user=current_user,
    )
    return await suite_service.get_suite_detail(suite_id, current_user=current_user)


@router.put("/{suite_id}", response_model=SuiteResponse)
async def update_suite(
    project_id: UUID,
    suite_id: UUID,
    request: SuiteUpdateRequest,
    suite_service: SuiteService = Depends(get_suite_service),
    current_user: User = Depends(get_current_user),
) -> SuiteResponse:
    await _assert_path_scope(
        project_id=project_id,
        suite_id=suite_id,
        suite_service=suite_service,
        current_user=current_user,
    )
    return await suite_service.update_suite(
        suite_id, request, current_user=current_user
    )


@router.delete("/{suite_id}", response_model=MessageResponse)
async def delete_suite(
    project_id: UUID,
    suite_id: UUID,
    suite_service: SuiteService = Depends(get_suite_service),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await _assert_path_scope(
        project_id=project_id,
        suite_id=suite_id,
        suite_service=suite_service,
        current_user=current_user,
    )
    await suite_service.delete_suite(suite_id, current_user=current_user)
    return MessageResponse(message="Suite deleted")


@router.get("/{suite_id}/cases", response_model=list[SuiteCaseResponse])
async def list_suite_cases(
    project_id: UUID,
    suite_id: UUID,
    suite_service: SuiteService = Depends(get_suite_service),
    current_user: User = Depends(get_current_user),
) -> list[SuiteCaseResponse]:
    await _assert_path_scope(
        project_id=project_id,
        suite_id=suite_id,
        suite_service=suite_service,
        current_user=current_user,
    )
    return await suite_service.list_suite_cases(suite_id, current_user=current_user)


@router.post(
    "/{suite_id}/cases",
    response_model=SuiteCasesBulkResponse,
    status_code=status.HTTP_200_OK,
)
async def bulk_add_suite_cases(
    project_id: UUID,
    suite_id: UUID,
    request: SuiteCasesBulkCreate,
    suite_service: SuiteService = Depends(get_suite_service),
    current_user: User = Depends(get_current_user),
) -> SuiteCasesBulkResponse:
    await _assert_path_scope(
        project_id=project_id,
        suite_id=suite_id,
        suite_service=suite_service,
        current_user=current_user,
    )
    return await suite_service.bulk_add_cases(
        suite_id, request, current_user=current_user
    )


@router.put("/{suite_id}/cases/order", response_model=list[SuiteCaseResponse])
async def reorder_suite_cases(
    project_id: UUID,
    suite_id: UUID,
    request: SuiteCasesReorderRequest,
    suite_service: SuiteService = Depends(get_suite_service),
    current_user: User = Depends(get_current_user),
) -> list[SuiteCaseResponse]:
    await _assert_path_scope(
        project_id=project_id,
        suite_id=suite_id,
        suite_service=suite_service,
        current_user=current_user,
    )
    return await suite_service.reorder_cases(
        suite_id, request, current_user=current_user
    )


@router.delete("/{suite_id}/cases/{test_case_id}", response_model=MessageResponse)
async def remove_suite_case(
    project_id: UUID,
    suite_id: UUID,
    test_case_id: UUID,
    suite_service: SuiteService = Depends(get_suite_service),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await _assert_path_scope(
        project_id=project_id,
        suite_id=suite_id,
        suite_service=suite_service,
        current_user=current_user,
    )
    await suite_service.remove_case(suite_id, test_case_id, current_user=current_user)
    return MessageResponse(message="Case removed from suite")
