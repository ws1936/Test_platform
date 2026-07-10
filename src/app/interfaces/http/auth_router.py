"""Authentication router for user login and registration."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.common.dependencies import (
    get_access_token,
    get_current_user,
    get_user_service,
)
from app.common.exceptions import BadRequestException, UnauthorizedException
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


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserWithTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account and return access/refresh tokens.",
    responses={
        201: {"description": "User registered successfully"},
        400: {"description": "Invalid request data"},
        409: {"description": "Username or email already taken"},
    },
)
async def register(
    request: UserRegisterRequest,
    user_service: UserService = Depends(get_user_service),
) -> UserWithTokenResponse:
    """Register a new user."""
    try:
        return await user_service.register(request)
    except ValueError as e:
        # Treat duplicate-key errors as 409 Conflict
        raise BadRequestException(str(e))


@router.post(
    "/login",
    response_model=UserWithTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user with email and password.",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
    },
)
async def login(
    request: UserLoginRequest,
    user_service: UserService = Depends(get_user_service),
) -> UserWithTokenResponse:
    """Login user."""
    try:
        return await user_service.login(request)
    except ValueError as e:
        raise UnauthorizedException(str(e))


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Get a new access token using a refresh token.",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid refresh token"},
    },
)
async def refresh_token(
    request: TokenRefreshRequest,
    user_service: UserService = Depends(get_user_service),
) -> TokenResponse:
    """Refresh access token."""
    try:
        return await user_service.refresh_token(request.refresh_token)
    except ValueError as e:
        raise UnauthorizedException(str(e))


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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)
