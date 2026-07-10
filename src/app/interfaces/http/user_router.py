"""User management router (admin + self-service)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import (
    get_current_superuser,
    get_current_user_id,
    get_user_service,
)
from app.common.exceptions import (
    AppException,
    BadRequestException,
    UserNotFoundException,
)
from app.domain.user.model import User
from app.domain.user.schema import (
    ChangePasswordRequest,
    MessageResponse,
    UserListQuery,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.domain.user.service import UserService


# Self-service router (mounted at /users/me)
me_router = APIRouter(prefix="/users/me", tags=["User - Self"])

# Admin router (mounted at /users)
admin_router = APIRouter(prefix="/users", tags=["User - Admin"])


@me_router.put(
    "/password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change current user's password",
    description=(
        "Change the current user's password. All previously issued "
        "tokens become invalid after a successful change."
    ),
    responses={
        200: {"description": "Password changed"},
        400: {"description": "Old password is incorrect"},
        401: {"description": "Not authenticated"},
    },
)
async def change_password(
    request: ChangePasswordRequest,
    user_id: UUID = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
) -> MessageResponse:
    try:
        await user_service.change_password(user_id, request)
    except UserNotFoundException as exc:
        # User deleted between token issuance and request — surface as 401.
        from app.common.exceptions import TokenInvalidException

        raise TokenInvalidException("User no longer exists") from exc
    except BadRequestException:
        raise
    except AppException as exc:
        # Service layer errors are already business-shaped; re-raise.
        raise exc
    return MessageResponse(message="Password changed successfully")


# === Admin endpoints (require superuser) ===
# In real RBAC, you'd check permissions here. For MVP we require is_superuser.


@admin_router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users (paginated, searchable)",
)
async def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_superuser),
) -> UserListResponse:
    query = UserListQuery(page=page, size=size, search=search)
    return await user_service.list_users(query)


@admin_router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user detail",
    responses={404: {"description": "User not found"}},
)
async def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_superuser),
) -> UserResponse:
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        raise UserNotFoundException()
    return UserResponse.model_validate(user)


@admin_router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user (admin)",
    description=(
        "Update user attributes. Setting ``status=0`` also bumps "
        "``token_version`` so the user's outstanding JWTs are rejected."
    ),
    responses={
        200: {"description": "Updated"},
        404: {"description": "User not found"},
    },
)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_superuser),
) -> UserResponse:
    return await user_service.update_user(user_id, request)


@admin_router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete user (status=0)",
    description=(
        "Soft-delete a user by setting status to 0 and bumping "
        "``token_version`` so their outstanding JWTs are rejected."
    ),
    responses={
        200: {"description": "Deleted"},
        404: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_superuser),
) -> MessageResponse:
    await user_service.delete_user(user_id)
    return MessageResponse(message="User deleted")