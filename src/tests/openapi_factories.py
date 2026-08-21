"""F022/F023 test factories — build SchemaModel / EndpointSchema with minimal boilerplate.

See ``docs/01-product/F022_PRECHECK.md`` §3 for the locked API surface.
Pure data factories; no DB / HTTP coupling.
"""
from __future__ import annotations
from typing import Any

from app.domain.openapi_importer.schema_model import (
    EndpointSchema,
    RequestSchema,
    SchemaModel,
    SecurityRequirement,
)


def make_schema(**overrides: Any) -> SchemaModel:
    """Build a SchemaModel with sensible defaults (type=string, format=None)."""
    return SchemaModel(**overrides)


def make_object_schema(
    properties: dict[str, dict[str, Any]],
    required: list[str] | None = None,
) -> SchemaModel:
    """Convenience: object schema with nested SchemaModel properties."""
    return SchemaModel(
        type="object",
        properties={
            name: make_schema(**props) for name, props in properties.items()
        },
        required=required or [],
    )


def make_endpoint_schema(**overrides: Any) -> EndpointSchema:
    """Build an EndpointSchema with sensible defaults."""
    defaults: dict[str, Any] = {
        "method": "GET",
        "path": "/test",
        "summary": "Test operation",
    }
    defaults.update(overrides)
    return EndpointSchema(**defaults)


# ---- Strategy-specific presets (F022 测试用) -----------------------------


def make_endpoint_with_required_fields(field_names: list[str]) -> EndpointSchema:
    """request_body 含 N 个 required 字段；用于 required_field_missing 策略测试。"""
    props = {name: {"type": "string"} for name in field_names}
    return make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(props, required=field_names),
            required=True,
        ),
    )


def make_endpoint_with_enum_property(
    enum_values: list[Any],
    field_name: str = "status",
) -> EndpointSchema:
    """request_body 含 1 个 enum 属性；用于 enum_coverage 策略测试。"""
    return make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {field_name: {"type": "string", "enum": enum_values}},
                required=[field_name],
            ),
        ),
    )


def make_endpoint_with_numeric_boundary(
    min_val: float | int,
    max_val: float | int,
    field_name: str = "age",
) -> EndpointSchema:
    """request_body 含 1 个 numeric 字段带 min/max；用于 boundary_min_max 策略测试。"""
    return make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {
                    field_name: {
                        "type": "integer",
                        "minimum": min_val,
                        "maximum": max_val,
                    }
                },
                required=[field_name],
            ),
        ),
    )


def make_endpoint_with_email_format() -> EndpointSchema:
    """request_body 含 1 个 format=email 字段；用于 format_invalid 策略测试。"""
    return make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {"email": {"type": "string", "format": "email"}},
                required=["email"],
            ),
        ),
    )


def make_endpoint_with_security(
    scheme_name: str = "bearerAuth",
    scopes: list[str] | None = None,
) -> EndpointSchema:
    """带 security 需求；用于 auth_missing 策略测试。"""
    return make_endpoint_schema(
        security=[SecurityRequirement(name=scheme_name, scopes=scopes or [])],
    )


__all__ = [
    "make_endpoint_schema",
    "make_endpoint_with_email_format",
    "make_endpoint_with_enum_property",
    "make_endpoint_with_numeric_boundary",
    "make_endpoint_with_required_fields",
    "make_endpoint_with_security",
    "make_object_schema",
    "make_schema",
]