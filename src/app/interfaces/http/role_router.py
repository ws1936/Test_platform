"""Role management router (admin only)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.common.dependencies import (
    get_current_user,
    get_role_service,
)
from app.common.exceptions import BadRequestException, NotFoundException
from app.domain.role.schema import (
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from app.domain.role.service import RoleService
from app.domain.user.model import User


router = APIRouter(prefix="/roles", tags=["Role"])


@router.get(
    "",
    response_model=list[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="List all roles",
)
async def list_roles(
    role_service: RoleService = Depends(get_role_service),
    _: User = Depends(get_current_user),
) -> list[RoleResponse]:
    roles = await role_service.list_roles()
    return [RoleResponse.model_validate(r) for r in roles]


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a role",
)
async def create_role(
    request: RoleCreateRequest,
    role_service: RoleService = Depends(get_role_service),
    _: User = Depends(get_current_user),
) -> RoleResponse:
    try:
        role = await role_service.create_role(request)
    except ValueError as e:
        raise BadRequestException(str(e))
    return RoleResponse.model_validate(role)


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get role detail",
)
async def get_role(
    role_id: UUID,
    role_service: RoleService = Depends(get_role_service),
    _: User = Depends(get_current_user),
) -> RoleResponse:
    role = await role_service.get_role(role_id)
    if not role:
        raise NotFoundException("Role not found")
    return RoleResponse.model_validate(role)


@router.put(
    "/{role_id}",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update role",
)
async def update_role(
    role_id: UUID,
    request: RoleUpdateRequest,
    role_service: RoleService = Depends(get_role_service),
    _: User = Depends(get_current_user),
) -> RoleResponse:
    try:
        role = await role_service.update_role(role_id, request)
    except ValueError as e:
        raise BadRequestException(str(e))
    return RoleResponse.model_validate(role)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete role",
)
async def delete_role(
    role_id: UUID,
    role_service: RoleService = Depends(get_role_service),
    _: User = Depends(get_current_user),
) -> None:
    try:
        await role_service.delete_role(role_id)
    except ValueError as e:
        raise BadRequestException(str(e))
