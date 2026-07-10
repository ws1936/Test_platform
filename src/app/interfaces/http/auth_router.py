"""Authentication router for user login and registration."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, Request, status

from app.common.dependencies import (
    get_access_token,
    get_current_user_with_version,
    get_user_service,
)
from app.common.exceptions import (
    AppException,
    CredentialsInvalidException,
    ForbiddenException,
    TooManyRequestsException,
)
from app.common.rate_limit import login_limiter, register_limiter
from app.common.security import TokenError, decode_token
from app.domain.user.model import User
from app.domain.user.schema import (
    LogoutResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserWithTokenResponse,
)
from app.domain.user.service import UserService
from uuid import UUID


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_key(request: Request, email: str | None = None) -> str:
    """Build a rate-limit key from client IP and (optionally) email."""
    ip = request.client.host if request.client else "unknown"
    if email:
        return f"{ip}|{email.lower()}"
    return ip


async def _optional_superuser(
    authorization: str | None = Header(default=None),
    user_service: UserService = Depends(get_user_service),
) -> User | None:
    """Resolve a superuser if a valid Bearer token is present.

    Returns ``None`` when no/invalid token is supplied. The function does
    not raise; callers decide whether the missing identity is allowed.
    This lets the public registration endpoint stay callable when no
    users exist yet (Review M-R1).
    """
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        user_uuid = UUID(sub)
    except (TypeError, ValueError):
        return None
    user = await user_service.get_user_by_id(user_uuid)
    if user is None:
        return None
    if int(payload.get("v", 0)) != user.token_version:
        return None
    if not user.is_active:
        return None
    if not user.is_superuser:
        return None
    return user


@router.post(
    "/register",
    response_model=UserWithTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Create a new user account and return access/refresh tokens. "
        "Open when the database has no users (the first account is "
        "automatically promoted to superuser). Otherwise an existing "
        "superuser must invoke the endpoint."
    ),
    responses={
        201: {"description": "User registered successfully"},
        403: {"description": "Registration requires a superuser token"},
        409: {"description": "Email or username already taken"},
        422: {"description": "Invalid request data"},
        429: {"description": "Too many registration attempts"},
    },
)
async def register(
    request: Request,
    payload: UserRegisterRequest,
    user_service: UserService = Depends(get_user_service),
    # Optional superuser token; only enforced once a user exists.
    superuser: User | None = Depends(
        _optional_superuser,
    ),
) -> UserWithTokenResponse:
    """Register a new user (Review M-R1).

    The endpoint is open ONLY when no users exist yet (the very first
    registration bootstraps the admin). After that, the caller must
    present a superuser Bearer token; otherwise the request is rejected
    with 403. This prevents anonymous account creation.
    """
    limiter = register_limiter()
    key = _client_key(request)
    if limiter.is_locked(key):
        raise TooManyRequestsException(
            details={"retry_after": limiter.lockout_remaining(key)},
        )

    # Check duplicates BEFORE the admin gate so a legitimate "already
    # exists" probe doesn't leak that admin auth is required.
    existing_email = await user_service.get_by_email(payload.email)
    if existing_email is not None:
        limiter.record_failure(key)
        from app.common.exceptions import EmailAlreadyExistsException

        raise EmailAlreadyExistsException()
    existing_username = await user_service.get_by_username(payload.username)
    if existing_username is not None:
        limiter.record_failure(key)
        from app.common.exceptions import UsernameAlreadyExistsException

        raise UsernameAlreadyExistsException()

    user_count = await user_service.count_users()
    is_first_user = user_count == 0
    if not is_first_user and superuser is None:
        limiter.record_failure(key)
        raise ForbiddenException(
            "Registration is restricted; superuser authentication required",
        )

    limiter.record_failure(key)
    try:
        result = await user_service.register(
            payload, is_first_user=is_first_user,
        )
    except AppException:
        limiter.record_success(key)
        raise
    return result


@router.post(
    "/login",
    response_model=UserWithTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user with email and password.",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        403: {"description": "Account disabled"},
        422: {"description": "Invalid request data"},
        429: {"description": "Too many failed login attempts"},
    },
)
async def login(
    request: Request,
    payload: UserLoginRequest,
    user_service: UserService = Depends(get_user_service),
) -> UserWithTokenResponse:
    """Authenticate a user by email + password.

    The limiter counts failures per (client IP, email) pair; a successful
    login clears the counter.
    """
    limiter = login_limiter()
    key = _client_key(request, payload.email)
    if limiter.is_locked(key):
        logger.warning(
            "auth.audit %s",
            {"event": "login.locked", "email": payload.email},
        )
        raise TooManyRequestsException(
            details={"retry_after": limiter.lockout_remaining(key)},
        )

    try:
        result = await user_service.login(payload)
    except CredentialsInvalidException:
        limiter.record_failure(key)
        raise
    except AppException:
        # Non-credential business errors (e.g. account disabled) should
        # not poison the credential-failure counter.
        raise

    limiter.record_success(key)
    return result


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Get a new access/refresh token pair using a refresh token.",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid refresh token"},
    },
)
async def refresh_token(
    payload: TokenRefreshRequest,
    user_service: UserService = Depends(get_user_service),
) -> TokenResponse:
    """Refresh access token."""
    return await user_service.refresh_token(payload.refresh_token)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout current user",
    description="Blacklist the current access token so it can no longer be used.",
    responses={
        200: {"description": "Logout successful"},
        401: {"description": "Not authenticated"},
    },
)
async def logout(
    access_token: str = Depends(get_access_token),
    current_user: User = Depends(get_current_user_with_version),
    user_service: UserService = Depends(get_user_service),
) -> LogoutResponse:
    """Logout the current user by invalidating the access token."""
    return await user_service.logout(access_token)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
    responses={
        200: {"description": "User information retrieved"},
        401: {"description": "Not authenticated"},
    },
)
async def get_me(
    current_user: User = Depends(get_current_user_with_version),
) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)