"""F022 TestIntent — declarative test case intent.

See ``docs/01-product/F022_SPEC.md`` §4 for the contract.  F022 produces
``TestIntent`` objects; F023 consumes them and emits
``TestCaseCreateRequest`` for persistence.  No DB / HTTP coupling here.
"""
from __future__ import annotations
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


StrategyName = Literal[
    "happy_path",
    "required_field_missing",
    "enum_coverage",
    "boundary_min_max",
    "format_invalid",
    "auth_missing",
]

BodyType = Literal["none", "json", "form", "raw"]
StatusMode = Literal["any_of", "not_in"]


class TestIntent(BaseModel):
    """F022 输出：单条声明式用例意图。

    F023 消费 TestIntent → TestCaseCreateRequest。
    F022 不落库；F023 才落 api_test_case 表。
    """

    model_config = ConfigDict(extra="forbid")

    # ---- 标识 ----
    intent_id: str = Field(description="uuid4().hex；F022 内唯一")
    strategy: StrategyName
    operation_id: str
    method: str
    path: str

    # ---- 用例字段（声明式；F023 据此生成 TestCaseCreateRequest）----
    name: str = Field(max_length=200)
    description: Optional[str] = None

    # 请求覆盖（相对 happy_path 的增量；None 表示沿用 happy_path）
    headers_override: Optional[dict[str, str]] = None
    query_override: Optional[dict[str, Any]] = None
    body_override: Optional[Any] = None
    body_type_override: Optional[BodyType] = None

    # ---- 断言（声明式；F023 据此生成 AssertionRule 列表）----
    assertions: list[dict[str, Any]] = Field(default_factory=list)

    # ---- 期望响应（status_code 期望 + 期望 body 字段）----
    expected_status_codes: list[int] = Field(default_factory=list)
    expected_status_mode: StatusMode = "any_of"


__all__ = [
    "BodyType",
    "StatusMode",
    "StrategyName",
    "TestIntent",
]