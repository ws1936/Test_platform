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
from app.domain.openapi_importer.service import OpenApiImportService
from app.domain.project.service import ProjectService
from app.domain.role.service import RoleService
from app.domain.suite.service import SuiteService
from app.domain.test_case.service import TestCaseService
from app.domain.test_run.service import TestRunService
from app.domain.user.model import User
from app.domain.user.service import UserService
from app.infrastructure.database.session import get_db


# "auto_error=False" so we can return the documented 401 (not the
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


async def get_suite_service(
    db: AsyncSession = Depends(get_db),
) -> SuiteService:
    """Get suite service dependency (F006)."""
    return SuiteService(db)


async def get_test_case_service(
    db: AsyncSession = Depends(get_db),
) -> TestCaseService:
    """Get test case service dependency (F007)."""
    return TestCaseService(db)


async def get_test_run_service(
    db: AsyncSession = Depends(get_db),
) -> "TestRunService":
    """Get test run service dependency (F010).

    Imported lazily inside the function body to avoid a circular
    import between :mod:`app.common.dependencies` and
    :mod:`app.domain.test_run.service` (the latter imports
    :mod:`app.common.exceptions`).
    """
    from app.domain.test_run.service import TestRunService

    return TestRunService(db)


async def get_openapi_import_service(
    db: AsyncSession = Depends(get_db),
) -> OpenApiImportService:
    """Get OpenAPI import service dependency (F012)."""
    return OpenApiImportService(db)


async def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract the raw access token string from Authorization header."""
    if credentials is None or not credentials.credentials:
        raise TokenInvalidException("Authentication required")
    if credentials.scheme.lower() != "bearer":
        raise TokenInvalidException("Authentication scheme must be Bearer")
    return credentials.credentials


async def _decode_user_id_from_token(access_token: str) -> tuple[UUID, int]:
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
    user_id, _ = await _decode_user_id_from_token(access_token)
    return user_id


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
) -> User:
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        raise TokenInvalidException("User no longer exists")
    return user


async def get_current_user_with_version(
    access_token: str = Depends(get_access_token),
    user_service: UserService = Depends(get_user_service),
) -> User:
    user_id, token_version = await _decode_user_id_from_token(access_token)
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        raise TokenInvalidException("User no longer exists")

    if token_version != user.token_version:
        raise TokenInvalidException("Token has been revoked")

    if not user.is_active:
        raise AccountDisabledException()

    return user


async def get_current_superuser(
    current_user: User = Depends(get_current_user_with_version),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action",
        )
    return current_user
