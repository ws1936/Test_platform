"""Project management router for F004 — API testing projects.

All endpoints require authentication. Authorization (owner / superuser)
is enforced inside the service layer.

Note on DELETE
--------------
``DELETE`` returns ``200 OK`` with a ``MessageResponse`` body rather than
``204 No Content`` because FastAPI forbids any response model on a 204
status code. This matches the convention used by ``user_router.delete_user``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import (
    get_current_user,
    get_current_user_with_version,
    get_project_service,
)
from app.domain.project.schema import (
    ProjectCreateRequest,
    ProjectListQuery,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.domain.project.service import ProjectService
from app.domain.user.model import User
from app.domain.user.schema import MessageResponse


router = APIRouter(prefix="/projects", tags=["Project"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
    description=(
        "Create a new API testing project. The authenticated user is "
        "recorded as the owner; clients cannot forge ownership."
    ),
    responses={
        201: {"description": "Project created"},
        401: {"description": "Not authenticated"},
        403: {"description": "Account disabled"},
        409: {"description": "Project name already exists"},
        422: {"description": "Validation error"},
    },
)
async def create_project(
    request: ProjectCreateRequest,
    project_service: ProjectService = Depends(get_project_service),
    # ``get_current_user_with_version`` enforces token_version + is_active so
    # that password changes / account disablements actually revoke write
    # access (Review TK-1).
    current_user: User = Depends(get_current_user_with_version),
) -> ProjectResponse:
    return await project_service.create_project(
        request, current_user=current_user
    )


@router.get(
    "",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="List projects owned by the current user",
    description=(
        "Returns a paginated list of projects **owned by the "
        "authenticated user**. Supports an optional name search via "
        "the ``search`` query parameter."
    ),
    responses={
        200: {"description": "Project list"},
        401: {"description": "Not authenticated"},
    },
)
async def list_projects(
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(default=None, description="按 name 模糊搜索"),
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user_with_version),
) -> ProjectListResponse:
    query = ProjectListQuery(page=page, size=size, search=search)
    return await project_service.list_projects(query, current_user=current_user)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project detail",
    description=(
        "Returns a single project. Authorization: project owner or "
        "superuser. Non-owners get 403; missing projects return 404."
    ),
    responses={
        200: {"description": "Project detail"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Project not found"},
    },
)
async def get_project(
    project_id: UUID,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user_with_version),
) -> ProjectResponse:
    project = await project_service.get_project(
        project_id, current_user=current_user
    )
    return ProjectResponse.model_validate(project)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a project",
    description=(
        "Update project name / description. Authorization: project "
        "owner or superuser. Non-owners get 403."
    ),
    responses={
        200: {"description": "Updated"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Project not found"},
        422: {"description": "Validation error"},
    },
)
async def update_project(
    project_id: UUID,
    request: ProjectUpdateRequest,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user_with_version),
) -> ProjectResponse:
    return await project_service.update_project(
        project_id, request, current_user=current_user
    )


@router.delete(
    "/{project_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a project",
    description=(
        "Hard-delete a project. Authorization: project owner or "
        "superuser. Non-owners get 403."
    ),
    responses={
        200: {"description": "Deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Project not found"},
    },
)
async def delete_project(
    project_id: UUID,
    project_service: ProjectService = Depends(get_project_service),
    current_user: User = Depends(get_current_user_with_version),
) -> MessageResponse:
    await project_service.delete_project(project_id, current_user=current_user)
    return MessageResponse(message="Project deleted")
