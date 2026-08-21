"""F021 SchemaModel data contracts (Pydantic v2).

See ``docs/01-product/F021_SPEC.md`` §4 for the design rationale and
``docs/04-rules/ADR.md`` ADR-008 for the locked decisions.

All models use ``extra="forbid"`` so that unrecognised OpenAPI keys are
surfaced as validation errors rather than silently ignored.  The
underlying parser already filters known fields — these models only
describe the *normalised* shape downstream stages (F022/F023) consume.
"""
from __future__ import annotations
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class SchemaModel(BaseModel):
    """OpenAPI Schema 深度模型（F021 数据契约）。

    Holds the normalised subset of OpenAPI 3.x Schema Object fields plus
    the F021-specific bookkeeping (``unresolved_branches`` /
    ``ref``).  All fields default to neutral values so partial specs
    degrade gracefully.
    """

    model_config = ConfigDict(extra="forbid")

    # ---- 通用 ----
    type: Optional[str] = Field(default=None)
    format: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    example: Optional[Any] = Field(default=None)
    default: Optional[Any] = Field(default=None)
    enum: Optional[list[Any]] = Field(default=None)
    const: Optional[Any] = Field(default=None)
    nullable: bool = Field(default=False)

    # ---- 数值（integer / number） ----
    minimum: Optional[float] = Field(default=None)
    maximum: Optional[float] = Field(default=None)
    exclusive_minimum: Optional[float] = Field(default=None)
    exclusive_maximum: Optional[float] = Field(default=None)
    multiple_of: Optional[float] = Field(default=None)

    # ---- 字符串 ----
    min_length: Optional[int] = Field(default=None, ge=0)
    max_length: Optional[int] = Field(default=None, ge=0)
    pattern: Optional[str] = Field(default=None)

    # ---- 数组 ----
    min_items: Optional[int] = Field(default=None, ge=0)
    max_items: Optional[int] = Field(default=None, ge=0)
    unique_items: bool = Field(default=False)
    items: Optional["SchemaModel"] = Field(default=None)

    # ---- 对象 ----
    properties: dict[str, "SchemaModel"] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    additional_properties: Optional[Union[bool, "SchemaModel"]] = Field(default=None)

    # ---- 复合 schema ----
    one_of: list["SchemaModel"] = Field(default_factory=list)
    any_of: list["SchemaModel"] = Field(default_factory=list)
    all_of: list["SchemaModel"] = Field(default_factory=list)

    # ---- F021 决策 3 标注字段 ----
    unresolved_branches: list["SchemaModel"] = Field(
        default_factory=list,
        description=(
            "oneOf/anyOf 中除首个分支外的其余分支；供 UI 提示 "
            "'F021 未完整建模此复合类型'。"
        ),
    )

    # ---- $ref 追踪 ----
    ref: Optional[str] = Field(
        default=None,
        description="最近一次解析的 $ref 路径；RefCycle 占位时为 '<cycle>'。",
    )


SchemaModel.model_rebuild()  # 支持前向引用


class ParameterSchema(BaseModel):
    """请求参数（F021 升级版；F012 parser 已有等价字段）。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    in_: str = Field(alias="in")  # header/query/path/cookie
    required: bool = False
    schema_model: SchemaModel = Field(alias="schema")
    description: Optional[str] = None
    example: Optional[Any] = None


class RequestSchema(BaseModel):
    """请求体（per content_type）。"""

    model_config = ConfigDict(extra="forbid")

    content_type: str
    schema_model: Optional[SchemaModel] = Field(default=None)
    required: bool = False


class ResponseSchema(BaseModel):
    """响应（per status_code + content_type）。"""

    model_config = ConfigDict(extra="forbid")

    status_code: str  # "200" / "2XX" / "default"
    content_type: str
    schema_model: Optional[SchemaModel] = Field(default=None)


class SecurityRequirement(BaseModel):
    """securitySchemes 需求（F022 auth_missing 策略的输入）。"""

    model_config = ConfigDict(extra="forbid")

    name: str  # e.g. "bearerAuth"
    scopes: list[str] = Field(default_factory=list)


class EndpointSchema(BaseModel):
    """单个 operation 的 F021 深度模型；F022 输入。"""

    model_config = ConfigDict(extra="forbid")

    operation_id: Optional[str] = None
    method: str
    path: str
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    parameters: list[ParameterSchema] = Field(default_factory=list)
    request_body: Optional[RequestSchema] = Field(default=None)
    responses: list[ResponseSchema] = Field(default_factory=list)
    security: list[SecurityRequirement] = Field(default_factory=list)


__all__ = [
    "SchemaModel",
    "ParameterSchema",
    "RequestSchema",
    "ResponseSchema",
    "SecurityRequirement",
    "EndpointSchema",
]