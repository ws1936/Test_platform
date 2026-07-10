"""Role Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    """Shared role fields."""

    name: str = Field(min_length=1, max_length=50, description="角色名称")
    description: Optional[str] = Field(default=None, max_length=255)
    permissions: Optional[list[str]] = Field(
        default=None,
        description="权限字符串列表，例如 ['user:read', 'project:write']",
    )


class RoleCreateRequest(RoleBase):
    """Role create request."""


class RoleUpdateRequest(BaseModel):
    """Role update request (all optional)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    permissions: Optional[list[str]] = Field(default=None)


class RoleResponse(BaseModel):
    """Role response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    permissions: Optional[list[str]] = None
    is_system: bool
    created_at: datetime
    updated_at: datetime
