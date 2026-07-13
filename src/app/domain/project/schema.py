"""Project Pydantic schemas.

Field set mirrors ``src/app/domain/project/model.py`` (DATABASE.md §3.3).
``owner_id`` is **not** accepted on create — the service layer derives it
from the authenticated user so the client cannot forge ownership.

Security note
-------------
``ProjectBase`` and ``ProjectUpdateRequest`` use ``extra="forbid"`` so
unknown fields are rejected with 422 instead of silently dropped. This
prevents clients from injecting fields like ``owner_id``, ``id``,
``created_at`` that the API contract does not declare.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# === Shared base ===


class ProjectBase(BaseModel):
    """Fields shared by create/update payloads.

    ``extra="forbid"`` rejects unknown fields so the client cannot inject
    fields the API does not declare (e.g. ``owner_id``, ``id``,
    ``created_at``). The service layer is the sole source of those fields.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100, description="项目名称")
    description: Optional[str] = Field(default=None, description="项目描述")


# === Request schemas ===


class ProjectCreateRequest(ProjectBase):
    """Project create request.

    Inherits ``extra="forbid"`` from :class:`ProjectBase`. ``owner_id``
    is intentionally omitted — the service layer sets it from the
    authenticated user context.
    """


class ProjectUpdateRequest(BaseModel):
    """Project update request (all fields optional).

    ``extra="forbid"`` — see :class:`ProjectBase` for rationale.
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None)


class ProjectListQuery(BaseModel):
    """Project list query parameters.

    Note: ``owner_id`` was removed — the list endpoint always scopes to
    the authenticated user's own projects. Filtering by other owners is
    out of scope for MVP.
    """

    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")
    search: Optional[str] = Field(default=None, description="按 name 模糊搜索")


# === Response schemas ===


class ProjectResponse(BaseModel):
    """Project detail response (returned by GET, POST, PUT)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Project list response with pagination."""

    items: list[ProjectResponse]
    total: int
    page: int
    size: int