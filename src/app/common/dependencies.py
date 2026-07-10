"""Common dependencies for dependency injection."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import UnauthorizedException
from app.common.security import decode_token
from app.domain.role.service import RoleService
from app.domain.user.model import User
from app.domain.user.service import UserService
from app.infrastructure.database.session import get_db


# Security scheme for Bearer token
security = HTTPBearer()


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


async def get_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Extract the raw access token string from Authorization header."""
    return credentials.credentials


async def get_current_user_id(
    access_token: str = Depends(get_access_token),
) -> UUID:
    """Extract and validate current user ID from JWT token."""
    payload = decode_token(access_token)

    if payload is None:
        raise UnauthorizedException("Invalid authentication credentials")

    # Check token type
    token_type = payload.get("type")
    if token_type != "access":
        raise UnauthorizedException("Invalid token type")

    # Get user ID from subject
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise UnauthorizedException("Invalid token payload")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Invalid user ID in token")

    return user_id


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Get current authenticated user."""
    try:
        user = await user_service.get_current_user(user_id)
        return user
    except ValueError as e:
        raise UnauthorizedException(str(e))


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action",
        )
    return current_user