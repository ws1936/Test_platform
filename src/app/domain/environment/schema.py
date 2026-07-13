"""Environment Pydantic schemas for F005 — API testing environments.

Field set mirrors ``src/app/domain/environment/model.py`` and
``docs/02-design/DATABASE.md`` §3.4.

Security note
-------------
``EnvironmentBase`` and ``EnvironmentUpdateRequest`` use
``extra="forbid"`` so unknown fields are rejected with 422 instead of
silently dropped. This prevents clients from injecting fields like
``project_id``, ``id`` or ``created_at`` that the API contract does
not declare (same hardening applied to ``ProjectBase``).
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# === Shared base ===


class EnvironmentBase(BaseModel):
    """Fields shared by create payloads.

    ``extra="forbid"`` rejects unknown fields so the client cannot
    inject fields the API does not declare (e.g. ``project_id``,
    ``id``, ``created_at``). The service layer is the sole source of
    those fields.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=50, description="环境名称，项目内唯一")
    base_url: str = Field(min_length=1, max_length=500, description="被测服务基础地址")
    headers: Optional[dict[str, Any]] = Field(
        default=None,
        description="环境级公共请求头（key→value）",
    )
    variables: Optional[dict[str, Any]] = Field(
        default=None,
        description="环境变量（key→value），用于 {{var}} 替换",
    )
    is_default: bool = Field(
        default=False,
        description="是否为该项目的默认环境；每项目最多一个默认环境",
    )

    @field_validator("base_url")
    @classmethod
    def _base_url_must_be_http(cls, value: str) -> str:
        """Reject obviously malformed base URLs at the boundary.

        We only accept ``http://`` / ``https://`` schemes — the engine
        uses ``httpx`` and cannot reach any other protocol. Anything
        else is almost certainly a client typo and would fail later
        during execution with a much worse error.
        """
        stripped = value.strip()
        if not (
            stripped.startswith("http://") or stripped.startswith("https://")
        ):
            raise ValueError("base_url must start with http:// or https://")
        return stripped


# === Request schemas ===


class EnvironmentCreateRequest(EnvironmentBase):
    """Environment create request.

    Inherits ``extra="forbid"`` from :class:`EnvironmentBase`. The
    ``project_id`` comes from the URL path, never from the request
    body, so the client cannot accidentally cross projects.
    """


class EnvironmentUpdateRequest(BaseModel):
    """Environment update request (all fields optional).

    ``extra="forbid"`` — see :class:`EnvironmentBase` for rationale.
    Only the supplied fields are touched; missing fields keep their
    current value. ``name`` and ``is_default`` updates go through the
    same uniqueness / single-default business rules as create.
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    base_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    headers: Optional[dict[str, Any]] = Field(default=None)
    variables: Optional[dict[str, Any]] = Field(default=None)
    is_default: Optional[bool] = Field(default=None)

    @field_validator("base_url")
    @classmethod
    def _base_url_must_be_http(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not (
            stripped.startswith("http://") or stripped.startswith("https://")
        ):
            raise ValueError("base_url must start with http:// or https://")
        return stripped


class EnvironmentListQuery(BaseModel):
    """Environment list query parameters.

    Environments are scoped to a project (the ``project_id`` path
    param) so the list is naturally bounded — no pagination is exposed
    for MVP. A project's environment count is expected to be small
    (typically dev / staging / prod).
    """

    search: Optional[str] = Field(default=None, description="按 name 模糊搜索")


# === Response schemas ===


class EnvironmentResponse(BaseModel):
    """Environment detail response (returned by GET, POST, PUT)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    base_url: str
    headers: Optional[dict[str, Any]] = None
    variables: Optional[dict[str, Any]] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class EnvironmentListResponse(BaseModel):
    """Environment list response (single project).

    The list endpoint is always scoped to a single project; no
    pagination envelope is required for MVP.
    """

    items: list[EnvironmentResponse]
    total: int
