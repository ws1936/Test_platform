"""User Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.common.security import validate_password_strength
from app.config import settings


# === Request Schemas ===


class UserRegisterRequest(BaseModel):
    """User registration request schema."""

    username: str = Field(min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(description="Email address (used to log in)")
    password: str = Field(
        min_length=settings.PASSWORD_MIN_LENGTH,
        max_length=128,
        description=(
            f"Password (>= {settings.PASSWORD_MIN_LENGTH} chars, "
            f"<= {settings.PASSWORD_MAX_BYTES} bytes after UTF-8 encoding)"
        ),
    )
    nickname: Optional[str] = Field(None, max_length=100, description="Nickname")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")

    @field_validator("password")
    @classmethod
    def _password_not_too_long_for_bcrypt(cls, value: str) -> str:
        # ``max_length`` above only counts characters, not bytes. We enforce
        # the byte length here so bcrypt never silently truncates.
        err = validate_password_strength(value)
        if err is not None:
            raise ValueError(err)
        return value


class UserLoginRequest(BaseModel):
    """User login request schema.

    Login is by email only; ``username`` was kept here historically and
    has been renamed to make the contract explicit (see Review C-R1).
    """

    email: EmailStr = Field(description="Email address")
    password: str = Field(description="Password")


class TokenRefreshRequest(BaseModel):
    """Token refresh request schema."""

    refresh_token: str = Field(description="Refresh token")


class ChangePasswordRequest(BaseModel):
    """Change password request schema (used by /users/me/password)."""

    old_password: str = Field(
        min_length=settings.PASSWORD_MIN_LENGTH,
        max_length=128,
        description="Current password",
    )
    new_password: str = Field(
        min_length=settings.PASSWORD_MIN_LENGTH,
        max_length=128,
        description="New password",
    )

    @field_validator("new_password")
    @classmethod
    def _new_password_strength(cls, value: str) -> str:
        err = validate_password_strength(value)
        if err is not None:
            raise ValueError(err)
        return value


class UserUpdateRequest(BaseModel):
    """Admin user update request (PUT /users/{id})."""

    nickname: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    status: Optional[int] = Field(default=None, ge=0, le=1, description="1=active, 0=disabled")
    role_id: Optional[UUID] = Field(default=None)
    is_superuser: Optional[bool] = Field(default=None)


class UserListQuery(BaseModel):
    """User list query parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")
    search: Optional[str] = Field(default=None, description="Search by email/username/nickname")


class UserListResponse(BaseModel):
    """User list response with pagination."""

    items: list["UserResponse"]
    total: int
    page: int
    size: int


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# === Response Schemas ===


class UserResponse(BaseModel):
    """Full user response schema (admin context)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    nickname: Optional[str] = None
    phone: Optional[str] = None
    status: int
    role_id: Optional[UUID] = None
    is_superuser: bool
    last_login_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UserPublicResponse(BaseModel):
    """Public-facing user response.

    Returned by login/register endpoints so we never leak ``is_superuser``
    or ``role_id`` to clients that only need a basic profile (Review
    M-R2 / M-S6).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    nickname: Optional[str] = None
    phone: Optional[str] = None
    last_login_time: Optional[datetime] = None
    created_at: datetime


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserWithTokenResponse(BaseModel):
    """User with token response schema.

    Uses :class:`UserPublicResponse` so login responses don't expose
    privileged fields.
    """

    user: UserPublicResponse
    token: TokenResponse


class LogoutResponse(BaseModel):
    """Logout response schema."""

    message: str = "Logged out successfully"


class RefreshResponse(BaseModel):
    """Refresh token response schema (admin endpoint, returns full pair)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# === Internal Schemas ===


class TokenPayload(BaseModel):
    """Token payload schema."""

    sub: str
    exp: int
    type: str = "access"


# Forward-reference resolution: UserListResponse references UserResponse.
UserListResponse.model_rebuild()