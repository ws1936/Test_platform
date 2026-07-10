"""User Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# === Request Schemas ===


class UserRegisterRequest(BaseModel):
    """User registration request schema."""

    username: str = Field(min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(description="邮箱")
    password: str = Field(min_length=8, max_length=128, description="密码")
    nickname: Optional[str] = Field(None, max_length=100, description="昵称")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")


class UserLoginRequest(BaseModel):
    """User login request schema."""

    username: str = Field(description="用户名")
    password: str = Field(description="密码")


class TokenRefreshRequest(BaseModel):
    """Token refresh request schema."""

    refresh_token: str = Field(description="刷新令牌")


class ChangePasswordRequest(BaseModel):
    """Change password request schema (used by /users/me/password)."""

    old_password: str = Field(min_length=8, max_length=128, description="旧密码")
    new_password: str = Field(min_length=8, max_length=128, description="新密码")


class UserUpdateRequest(BaseModel):
    """Admin user update request (PUT /users/{id})."""

    nickname: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    status: Optional[int] = Field(default=None, ge=0, le=1, description="1=active, 0=disabled")
    role_id: Optional[UUID] = Field(default=None)
    is_superuser: Optional[bool] = Field(default=None)


class UserListQuery(BaseModel):
    """User list query parameters."""

    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页数量")
    search: Optional[str] = Field(default=None, description="按邮箱/姓名模糊搜索")


class UserListResponse(BaseModel):
    """User list response with pagination."""

    items: list[UserResponse]
    total: int
    page: int
    size: int


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# === Response Schemas ===


class UserResponse(BaseModel):
    """User response schema."""

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


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserWithTokenResponse(BaseModel):
    """User with token response schema."""

    user: UserResponse
    token: TokenResponse


class LogoutResponse(BaseModel):
    """Logout response schema."""

    message: str = "退出登录成功"


class RefreshResponse(BaseModel):
    """Refresh token response schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


# === Internal Schemas ===


class TokenPayload(BaseModel):
    """Token payload schema."""

    sub: str
    exp: int
    type: str = "access"