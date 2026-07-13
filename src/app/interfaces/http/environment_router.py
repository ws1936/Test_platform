"""Environment management router for F005 — API testing environments.

All endpoints require authentication. Authorization (project owner or
superuser) is enforced inside the service layer.

Endpoints (matches ``docs/03-api/API_GUIDE.md`` §3.5):

* ``POST   /projects/{project_id}/environments``       — create
* ``GET    /projects/{project_id}/environments``       — list (scoped)
* ``GET    /environments/{environment_id}``            — detail
* ``PUT    /environments/{environment_id}``            — update
* ``DELETE /environments/{environment_id}``            — delete (refuses
  if default; caller must set another env as default first)
* ``POST   /environments/{environment_id}/set-default`` — promote to
  project default (extra endpoint beyond API_GUIDE; needed because
  deleting the current default requires first transferring the
  default to a sibling environment).

Note on DELETE
--------------
``DELETE`` returns ``200 OK`` with a ``MessageResponse`` body rather
than ``204 No Content`` because FastAPI forbids any response model
on a 204 status code. This matches the convention used by
``project_router.delete_project`` and ``user_router.delete_user``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import get_current_user, get_environment_service
from app.domain.environment.schema import (
    EnvironmentCreateRequest,
    EnvironmentListQuery,
    EnvironmentListResponse,
    EnvironmentResponse,
    EnvironmentUpdateRequest,
)
from app.domain.environment.service import EnvironmentService
from app.domain.user.model import User
from app.domain.user.schema import MessageResponse


# Nested routes under a project (create / list) get the project prefix;
# the remaining endpoints live under a flat ``/environments`` prefix
# so the URL path reflects "this resource has its own identity".
project_router = APIRouter(prefix="/projects", tags=["Environment"])
environment_router = APIRouter(prefix="/environments", tags=["Environment"])


# === Project-scoped endpoints (create + list) ===


@project_router.post(
    "/{project_id}/environments",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an environment",
    description=(
        "Create a new API testing environment under the given project. "
        "Authorization: project owner or superuser. Returns 409 if the "
        "environment name is already used in the project, 403 if the "
        "caller is neither owner nor admin, 404 if the project does "
        "not exist."
    ),
    responses={
        201: {"description": "Environment created"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Project not found"},
        409: {"description": "Environment name already exists"},
        422: {"description": "Validation error"},
    },
)
async def create_environment(
    project_id: UUID,
    request: EnvironmentCreateRequest,
    environment_service: EnvironmentService = Depends(get_environment_service),
    current_user: User = Depends(get_current_user),
) -> EnvironmentResponse:
    return await environment_service.create_environment(
        project_id, request, current_user=current_user
    )


@project_router.get(
    "/{project_id}/environments",
    response_model=EnvironmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List environments of a project",
    description=(
        "Returns every environment belonging to the project. "
        "Authorization: project owner or superuser. Supports an "
        "optional name search via the ``search`` query parameter."
    ),
    responses={
        200: {"description": "Environment list"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Project not found"},
    },
)
async def list_environments(
    project_id: UUID,
    search: str | None = Query(default=None, description="按 name 模糊搜索"),
    environment_service: EnvironmentService = Depends(get_environment_service),
    current_user: User = Depends(get_current_user),
) -> EnvironmentListResponse:
    query = EnvironmentListQuery(search=search)
    return await environment_service.list_environments(
        project_id, query, current_user=current_user
    )


# === Environment-scoped endpoints (detail / update / delete / default) ===


@environment_router.get(
    "/{environment_id}",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get environment detail",
    description=(
        "Returns a single environment. Authorization: project owner "
        "or superuser. Non-owners get 403; missing environments "
        "return 404."
    ),
    responses={
        200: {"description": "Environment detail"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Environment not found"},
    },
)
async def get_environment(
    environment_id: UUID,
    environment_service: EnvironmentService = Depends(get_environment_service),
    current_user: User = Depends(get_current_user),
) -> EnvironmentResponse:
    env = await environment_service.get_environment(
        environment_id, current_user=current_user
    )
    return EnvironmentResponse.model_validate(env)


@environment_router.put(
    "/{environment_id}",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an environment",
    description=(
        "Update environment fields. Authorization: project owner or "
        "superuser. Setting ``is_default=true`` demotes the previous "
        "default in the same transaction."
    ),
    responses={
        200: {"description": "Updated"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Environment not found"},
        409: {"description": "Environment name already exists"},
        422: {"description": "Validation error"},
    },
)
async def update_environment(
    environment_id: UUID,
    request: EnvironmentUpdateRequest,
    environment_service: EnvironmentService = Depends(get_environment_service),
    current_user: User = Depends(get_current_user),
) -> EnvironmentResponse:
    return await environment_service.update_environment(
        environment_id, request, current_user=current_user
    )


@environment_router.delete(
    "/{environment_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete an environment",
    description=(
        "Hard-delete an environment. Authorization: project owner or "
        "superuser. Returns 409 if the environment is the project's "
        "default — the caller must first promote a sibling to default."
    ),
    responses={
        200: {"description": "Deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Environment not found"},
        409: {"description": "Environment is the default and cannot be deleted"},
    },
)
async def delete_environment(
    environment_id: UUID,
    environment_service: EnvironmentService = Depends(get_environment_service),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    await environment_service.delete_environment(
        environment_id, current_user=current_user
    )
    return MessageResponse(message="Environment deleted")


@environment_router.post(
    "/{environment_id}/set-default",
    response_model=EnvironmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Promote an environment to the project default",
    description=(
        "Promote this environment to the project's default. The "
        "previous default (if any) is demoted in the same "
        "transaction. Authorization: project owner or superuser."
    ),
    responses={
        200: {"description": "Promoted to default"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not owner / not admin"},
        404: {"description": "Environment not found"},
    },
)
async def set_default_environment(
    environment_id: UUID,
    environment_service: EnvironmentService = Depends(get_environment_service),
    current_user: User = Depends(get_current_user),
) -> EnvironmentResponse:
    return await environment_service.set_default_environment(
        environment_id, current_user=current_user
    )
