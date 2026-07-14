"""Pydantic request and response schemas for F007 API test cases.

Field set mirrors ``src/app/domain/test_case/model.py``. F007 only
*stores* the request definition and assertions; execution lives in
F010 (pytest execution) and F009 (assertion engine) — see PRD §5.4.

Security note
-------------
``TestCaseBase`` and ``TestCaseUpdateRequest`` use ``extra="forbid"`` so
unknown fields are rejected with 422 instead of being silently dropped.
This prevents clients from injecting fields like ``project_id``,
``id`` or ``created_at`` that the API contract does not declare
(same hardening applied to ``ProjectBase`` / ``EnvironmentBase``).

Field mapping
-------------
The database column ``api_test_cases.status`` is an int (1=enabled,
0=disabled) so it can be reused by both F005-style "1 row per
logical flag" and an F009 boolean column at zero migration cost.  The
public API exposes ``enabled: bool`` because that's what callers
actually want to send — the int↔bool mapping lives in the service
layer's ``_to_response`` helper.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# === Constants ===

# PRD §5.4 — the test runner must support these five methods.
ALLOWED_METHODS: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE")

# PRD §5.4 + API_GUIDE §5 — body content-type taxonomy.
ALLOWED_BODY_TYPES: tuple[str, ...] = ("none", "json", "form", "raw")


# === Shared base ===


class TestCaseBase(BaseModel):
    """Fields shared by create payloads.

    ``extra="forbid"`` rejects unknown fields so the client cannot
    inject fields the API does not declare (e.g. ``project_id``,
    ``id``, ``created_at``).  The service layer is the sole source of
    those fields.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        max_length=200,
        description="用例名称，仅用于展示，不要求项目内唯一",
    )
    method: str = Field(
        default="GET",
        description="HTTP 方法：GET / POST / PUT / PATCH / DELETE",
    )
    path: str = Field(
        default="/",
        min_length=1,
        max_length=500,
        description="请求路径（相对环境 base_url），必须以 / 开头",
    )
    headers: Optional[dict[str, Any]] = Field(
        default=None,
        description="用例级请求头（key→value），与合并后执行",
    )
    query_params: Optional[dict[str, Any]] = Field(
        default=None,
        description="查询参数（key→value），与执行时合并到 URL",
    )
    body_type: str = Field(
        default="none",
        description="请求体类型：none / json / form / raw",
    )
    body: Optional[Any] = Field(
        default=None,
        description="请求体载荷，按 body_type 解释（json→对象，form→键值，raw→字符串）",
    )
    assertions: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="断言规则列表，结构由 F009 决定；F007 仅做存储",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=600,
        description="单条用例执行超时时间（秒），最大 600 秒",
    )
    enabled: bool = Field(
        default=True,
        description="是否启用该用例；禁用的用例不会出现在执行批次中",
    )

    @field_validator("method")
    @classmethod
    def _normalize_method(cls, value: str) -> str:
        """Accept any-case input but normalise to uppercase."""
        normalized = value.upper()
        if normalized not in ALLOWED_METHODS:
            raise ValueError(
                f"method must be one of {list(ALLOWED_METHODS)}"
            )
        return normalized

    @field_validator("body_type")
    @classmethod
    def _validate_body_type(cls, value: str) -> str:
        if value not in ALLOWED_BODY_TYPES:
            raise ValueError(
                f"body_type must be one of {list(ALLOWED_BODY_TYPES)}"
            )
        return value

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        """Reject paths that don't start with '/' so the engine never
        has to interpret a relative URL on its own."""
        stripped = value.strip()
        if not stripped.startswith("/"):
            raise ValueError("path must start with '/'")
        return stripped


# === Request schemas ===


class TestCaseCreateRequest(TestCaseBase):
    """Create payload.

    ``project_id`` and ``suite_id`` come from the URL path, never from
    the request body — the client cannot accidentally cross projects.
    """


class TestCaseUpdateRequest(BaseModel):
    """Partial update (all fields optional).

    ``extra="forbid"`` — see :class:`TestCaseBase` for rationale. Only
    the supplied fields are touched; missing fields keep their current
    value. The same per-field validators from the create schema are
    re-applied so PATCH-shaped misuse still surfaces as 422.
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    method: Optional[str] = None
    path: Optional[str] = Field(default=None, min_length=1, max_length=500)
    headers: Optional[dict[str, Any]] = None
    query_params: Optional[dict[str, Any]] = None
    body_type: Optional[str] = None
    body: Optional[Any] = None
    assertions: Optional[list[dict[str, Any]]] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=600)
    enabled: Optional[bool] = None

    @field_validator("method")
    @classmethod
    def _normalize_method(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.upper()
        if normalized not in ALLOWED_METHODS:
            raise ValueError(
                f"method must be one of {list(ALLOWED_METHODS)}"
            )
        return normalized

    @field_validator("body_type")
    @classmethod
    def _validate_body_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in ALLOWED_BODY_TYPES:
            raise ValueError(
                f"body_type must be one of {list(ALLOWED_BODY_TYPES)}"
            )
        return value

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped.startswith("/"):
            raise ValueError("path must start with '/'")
        return stripped


# === Response schemas ===


class TestCaseResponse(BaseModel):
    """Test case detail response (returned by GET, POST, PUT).

    ``enabled`` is derived from the database ``status`` int (1=enabled,
    0=disabled) inside :py:meth:`TestCaseService._to_response` so the
    wire format stays boolean while the storage stays portable across
    SQLite + PostgreSQL.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    method: str
    path: str
    headers: Optional[dict[str, Any]] = None
    query_params: Optional[dict[str, Any]] = None
    body_type: str
    body: Optional[Any] = None
    assertions: Optional[list[dict[str, Any]]] = None
    timeout_seconds: int
    sort_order: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class TestCaseListResponse(BaseModel):
    """Test case list response (project-scoped)."""

    items: list[TestCaseResponse]
    total: int