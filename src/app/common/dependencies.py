"""Common dependencies for dependency injection."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    AccountDisabledException,
    TokenInvalidException,
)
from app.common.security import TokenError, decode_token
from app.domain.environment.service import EnvironmentService
from app.domain.project.service import ProjectService
from app.domain.role.service import RoleService
from app.domain.user.model import User
from app.domain.user.service import UserService
from app.infrastructure.database.session import get_db


# ``auto_error=False`` so we can return the documented 401 (not the
# default 403) when the Authorization header is missing.
security = HTTPBearer(auto_error=False)


async def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    """Get user service dependency."""
    return UserService(db)


async def get_role_service(
    db: AsyncSession = Depends(get_db),
) -> RoleService:
    """Get role service dependency."""
    return RoleService(db)


async def get_project_service(
    db: AsyncSession = Depends(get_db),
) -> ProjectService:
    """Get project service dependency."""
    return ProjectService(db)


async def get_environment_service(
    db: AsyncSession = Depends(get_db),
) -> EnvironmentService:
    """Get environment service dependency (F005)."""
    return EnvironmentService(db)


async def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract the raw access token string from Authorization header.

    Raises 401 ``TokenInvalidException`` when the header is missing or
    uses the wrong scheme, matching ``API_GUIDE.md`` §2.3
    (Review M-S3).
    """
    if credentials is None or not credentials.credentials:
        raise TokenInvalidException("Authentication required")
    if credentials.scheme.lower() != "bearer":
        raise TokenInvalidException("Authentication scheme must be Bearer")
    return credentials.credentials


async def _decode_user_id_from_token(access_token: str) -> tuple[UUID, int]:
    """Decode ``access_token`` and return ``(user_id, token_version)``.

    Raises ``TokenInvalidException`` on any failure.
    """
    try:
        payload = decode_token(access_token, expected_type="access")
    except TokenError as exc:
        raise TokenInvalidException(str(exc)) from exc

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise TokenInvalidException("Invalid token payload")
    try:
        user_uuid = UUID(user_id_str)
    except (TypeError, ValueError) as exc:
        raise TokenInvalidException("Invalid token subject") from exc

    return user_uuid, int(payload.get("v", 0))


async def get_current_user_id(
    access_token: str = Depends(get_access_token),
) -> UUID:
    """Extract and validate current user ID from JWT token."""
    user_id, _ = await _decode_user_id_from_token(access_token)
    return user_id


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Resolve the JWT subject into a live ``User`` row.

    The ``token_version`` claim on the JWT is compared to the current
    value on the user record so password changes / admin lock-outs
    invalidate previously issued tokens (Review C-S5).
    """
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        raise TokenInvalidException("User no longer exists")
    return user


async def get_current_user_with_version(
    access_token: str = Depends(get_access_token),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Variant of ``get_current_user`` that also enforces ``token_version``."""
    user_id, token_version = await _decode_user_id_from_token(access_token)
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        raise TokenInvalidException("User no longer exists")

    if token_version != user.token_version:
        raise TokenInvalidException("Token has been revoked")

    if not user.is_active:
        # Account was disabled after the token was issued.
        raise AccountDisabledException()

    return user


async def get_current_superuser(
    current_user: User = Depends(get_current_user_with_version),
) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action",
        )
    return current_user