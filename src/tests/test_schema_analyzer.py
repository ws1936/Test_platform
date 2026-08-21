"""Tests for F021 Schema Analyzer.

Covers T1–T20 in ``docs/01-product/F021_SPEC.md`` §11.1.
"""
from __future__ import annotations
import pytest

from app.domain.openapi_importer.exceptions import OpenApiParseError
from app.domain.openapi_importer.parser import Operation
from app.domain.openapi_importer.schema_analyzer import SchemaAnalyzer
from app.domain.openapi_importer.schema_model import (
    EndpointSchema,
    ParameterSchema,
    RequestSchema,
    ResponseSchema,
    SchemaModel,
    SecurityRequirement,
)


@pytest.fixture
def analyzer() -> SchemaAnalyzer:
    return SchemaAnalyzer()


# ---------------------------------------------------------------------------
# T1 — simple string schema
# ---------------------------------------------------------------------------
def test_t1_simple_string_schema(analyzer: SchemaAnalyzer) -> None:
    sm = analyzer.analyze_schema(
        {"type": "string", "minLength": 2, "maxLength": 32},
        {},
    )
    assert sm.type == "string"
    assert sm.min_length == 2
    assert sm.max_length == 32
    assert sm.minimum is None  # numeric fields untouched


# ---------------------------------------------------------------------------
# T2 — integer boundary (min/max/exclusive/multiple_of)
# ---------------------------------------------------------------------------
def test_t2_integer_boundary_fields(analyzer: SchemaAnalyzer) -> None:
    sm = analyzer.analyze_schema(
        {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "exclusiveMinimum": 0,
            "exclusiveMaximum": 101,
            "multipleOf": 2,
        },
        {},
    )
    assert sm.type == "integer"
    assert sm.minimum == 1
    assert sm.maximum == 100
    assert sm.exclusive_minimum == 0
    assert sm.exclusive_maximum == 101
    assert sm.multiple_of == 2


# ---------------------------------------------------------------------------
# T3 — enum array
# ---------------------------------------------------------------------------
def test_t3_enum_array(analyzer: SchemaAnalyzer) -> None:
    sm = analyzer.analyze_schema({"type": "string", "enum": ["a", "b", "c"]}, {})
    assert sm.enum == ["a", "b", "c"]


def test_t3_enum_empty_list_is_legal(analyzer: SchemaAnalyzer) -> None:
    sm = analyzer.analyze_schema({"type": "string", "enum": []}, {})
    assert sm.enum == []


# ---------------------------------------------------------------------------
# T4 — object + required
# ---------------------------------------------------------------------------
def test_t4_object_with_required(analyzer: SchemaAnalyzer) -> None:
    sm = analyzer.analyze_schema(
        {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["id"],
        },
        {},
    )
    assert sm.type == "object"
    assert "id" in sm.properties
    assert "name" in sm.properties
    assert sm.properties["id"].type == "string"
    assert sm.required == ["id"]


# ---------------------------------------------------------------------------
# T5 — array + items + min/maxItems
# ---------------------------------------------------------------------------
def test_t5_array_with_items(analyzer: SchemaAnalyzer) -> None:
    sm = analyzer.analyze_schema(
        {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 1,
            "maxItems": 10,
        },
        {},
    )
    assert sm.type == "array"
    assert sm.items is not None
    assert sm.items.type == "integer"
    assert sm.min_items == 1
    assert sm.max_items == 10


# ---------------------------------------------------------------------------
# T6 — $ref one-level resolution
# ---------------------------------------------------------------------------
def test_t6_ref_one_level(analyzer: SchemaAnalyzer) -> None:
    components = {
        "Pet": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        }
    }
    sm = analyzer.analyze_schema({"$ref": "#/components/schemas/Pet"}, components)
    assert sm.type == "object"
    assert "id" in sm.properties
    assert sm.required == ["id"]


# ---------------------------------------------------------------------------
# T7 — $ref nested (3 levels)
# ---------------------------------------------------------------------------
def test_t7_ref_nested(analyzer: SchemaAnalyzer) -> None:
    components = {
        "C": {"type": "object", "properties": {"leaf": {"type": "string"}}},
        "B": {"$ref": "#/components/schemas/C"},
        "A": {"$ref": "#/components/schemas/B"},
    }
    sm = analyzer.analyze_schema({"$ref": "#/components/schemas/A"}, components)
    assert sm.type == "object"
    assert "leaf" in sm.properties
    assert sm.properties["leaf"].type == "string"


# ---------------------------------------------------------------------------
# T8 — $ref depth limit (12 layers → OpenApiParseError)
# ---------------------------------------------------------------------------
def test_t8_ref_depth_limit_exceeded(analyzer: SchemaAnalyzer) -> None:
    # Build a 12-deep chain: L1 → L2 → ... → L12
    # Each level is a fresh dict that references the next.
    components: dict = {}
    for i in range(12, 0, -1):
        if i == 1:
            components["L1"] = {"type": "string"}
        else:
            components[f"L{i}"] = {"$ref": f"#/components/schemas/L{i - 1}"}
    with pytest.raises(OpenApiParseError) as exc:
        analyzer.analyze_schema({"$ref": "#/components/schemas/L12"}, components)
    assert exc.value.details is not None
    assert exc.value.details.get("reason") == "ref_depth"


# ---------------------------------------------------------------------------
# T9 — $ref cycle (A → B → A) returns RefCycle placeholder, no exception
# ---------------------------------------------------------------------------
def test_t9_ref_cycle_returns_placeholder(analyzer: SchemaAnalyzer) -> None:
    # NOTE: SchemaAnalyzer uses id(raw) for cycle detection.  To trigger a
    # cycle we must share the *same* dict instance between A and B's
    # ``$ref`` target.  Hand-build the components dict so that A and B
    # both point to the SAME dict that references itself.
    loop_target: dict = {"type": "object"}
    loop_target["$ref"] = "#/components/schemas/Loop"  # self-ref
    components = {"Loop": loop_target}
    sm = analyzer.analyze_schema({"$ref": "#/components/schemas/Loop"}, components)
    # Cycle is detected at the first revisit; result is a placeholder.
    assert sm.ref == "<cycle>"


# ---------------------------------------------------------------------------
# T10 — oneOf take-first + unresolved_branches
# ---------------------------------------------------------------------------
def test_t10_one_of_unresolved(analyzer: SchemaAnalyzer) -> None:
    raw = {
        "oneOf": [
            {"type": "string"},
            {"type": "integer"},
            {"type": "boolean"},
        ]
    }
    sm = analyzer.analyze_schema(raw, {})
    # First branch taken as the normalised target
    assert sm.type == "string"
    # Remaining branches preserved
    assert len(sm.unresolved_branches) == 2
    assert sm.unresolved_branches[0].type == "integer"
    assert sm.unresolved_branches[1].type == "boolean"
    # one_of mirrors unresolved_branches
    assert len(sm.one_of) == 2


# ---------------------------------------------------------------------------
# T11 — anyOf take-first + unresolved_branches
# ---------------------------------------------------------------------------
def test_t11_any_of_unresolved(analyzer: SchemaAnalyzer) -> None:
    raw = {
        "anyOf": [
            {"type": "string"},
            {"type": "integer"},
        ]
    }
    sm = analyzer.analyze_schema(raw, {})
    assert sm.type == "string"
    assert len(sm.unresolved_branches) == 1
    assert sm.unresolved_branches[0].type == "integer"
    assert len(sm.any_of) == 1


# ---------------------------------------------------------------------------
# T12 — allOf shallow merge + required dedup
# ---------------------------------------------------------------------------
def test_t12_all_of_shallow_merge(analyzer: SchemaAnalyzer) -> None:
    raw = {
        "allOf": [
            {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "required": ["a", "b"],
            },
            {
                "type": "object",
                "properties": {"b": {"type": "string"}, "c": {"type": "string"}},
                "required": ["b", "c"],
            },
        ]
    }
    sm = analyzer.analyze_schema(raw, {})
    assert sm.type == "object"
    assert set(sm.properties.keys()) == {"a", "b", "c"}
    # required deduped
    assert sorted(sm.required) == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# T13 — allOf type conflict raises OpenApiParseError
# ---------------------------------------------------------------------------
def test_t13_all_of_type_conflict(analyzer: SchemaAnalyzer) -> None:
    raw = {
        "allOf": [
            {"type": "string"},
            {"type": "integer"},
        ]
    }
    with pytest.raises(OpenApiParseError) as exc:
        analyzer.analyze_schema(raw, {})
    assert exc.value.details is not None
    assert exc.value.details.get("reason") == "allof_type_conflict"
    assert exc.value.details.get("existing") == "string"
    assert exc.value.details.get("incoming") == "integer"


# ---------------------------------------------------------------------------
# T14 — format field passthrough
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "fmt",
    ["email", "uuid", "date-time", "int32", "int64", "float", "double", "uri"],
)
def test_t14_format_field_passthrough(analyzer: SchemaAnalyzer, fmt: str) -> None:
    sm = analyzer.analyze_schema({"type": "string", "format": fmt}, {})
    assert sm.format == fmt


# ---------------------------------------------------------------------------
# T15 — nullable field (OpenAPI 3.0)
# ---------------------------------------------------------------------------
def test_t15_nullable(analyzer: SchemaAnalyzer) -> None:
    sm = analyzer.analyze_schema({"type": "string", "nullable": True}, {})
    assert sm.nullable is True


def test_t15_nullable_default_false(analyzer: SchemaAnalyzer) -> None:
    sm = analyzer.analyze_schema({"type": "string"}, {})
    assert sm.nullable is False


# ---------------------------------------------------------------------------
# T16 — securitySchemes extraction via analyze(global_security=...)
# ---------------------------------------------------------------------------
def test_t16_security_schemes_extraction(analyzer: SchemaAnalyzer) -> None:
    op = Operation(
        operation_id="x",
        method="GET",
        path="/x",
        name="x",
    )
    ep = analyzer.analyze(
        op,
        components_schemas={},
        global_security=[{"bearerAuth": []}],
    )
    assert len(ep.security) == 1
    assert ep.security[0].name == "bearerAuth"
    assert ep.security[0].scopes == []


# ---------------------------------------------------------------------------
# T17 — multi response code coverage
# ---------------------------------------------------------------------------
def test_t17_multi_response_codes(analyzer: SchemaAnalyzer) -> None:
    op = Operation(
        operation_id="multi",
        method="POST",
        path="/pets",
        name="Create",
        raw_responses={
            "200": {"description": "ok", "content": {"application/json": {"schema": {"type": "object"}}}},
            "400": {"description": "bad request"},
            "404": {"description": "not found"},
            "default": {"description": "unexpected"},
        },
    )
    ep = analyzer.analyze(op, components_schemas={})
    codes = [r.status_code for r in ep.responses]
    assert "200" in codes
    assert "400" in codes
    assert "404" in codes
    assert "default" in codes
    # The 200 carries a schema_model; others don't
    r200 = next(r for r in ep.responses if r.status_code == "200")
    assert r200.schema_model is not None
    assert r200.schema_model.type == "object"
    r400 = next(r for r in ep.responses if r.status_code == "400")
    assert r400.schema_model is None


# ---------------------------------------------------------------------------
# T18 — F012 backward compatibility (Operation without raw_* fields)
# ---------------------------------------------------------------------------
def test_t18_backward_compatible_with_f012_operation(
    analyzer: SchemaAnalyzer,
) -> None:
    # F012 parser may emit Operation objects without raw_* (e.g. test
    # fixtures).  SchemaAnalyzer must still produce a valid EndpointSchema.
    op = Operation(
        operation_id="legacy",
        method="GET",
        path="/legacy",
        name="Legacy",
        request_headers={},
        request_query={},
    )
    ep = analyzer.analyze(op, components_schemas={})
    assert isinstance(ep, EndpointSchema)
    assert ep.method == "GET"
    assert ep.path == "/legacy"
    assert ep.parameters == []
    assert ep.request_body is None
    assert ep.responses == []


# ---------------------------------------------------------------------------
# T19 — unsupported $ref shape returns as-is (no exception)
# ---------------------------------------------------------------------------
def test_t19_unsupported_ref_shape_returns_as_is(
    analyzer: SchemaAnalyzer,
) -> None:
    sm = analyzer.analyze_schema(
        {"$ref": "external.json#/Pet"},  # not a local ref
        {},
    )
    # The "as-is" branch returns a SchemaModel with no fields populated
    # (the $ref key itself is *not* transferred).
    assert sm.type is None
    assert sm.format is None


# ---------------------------------------------------------------------------
# T20 — top-level without explicit type but with properties → object
# ---------------------------------------------------------------------------
def test_t20_type_inferred_from_properties(analyzer: SchemaAnalyzer) -> None:
    sm = analyzer.analyze_schema(
        {
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
        },
        {},
    )
    assert sm.type == "object"
    assert "x" in sm.properties


def test_t20_type_inferred_from_items(analyzer: SchemaAnalyzer) -> None:
    sm = analyzer.analyze_schema(
        {"items": {"type": "integer"}},
        {},
    )
    assert sm.type == "array"
    assert sm.items is not None
    assert sm.items.type == "integer"


# ---------------------------------------------------------------------------
# Extra: analyze_parameter passes through
# ---------------------------------------------------------------------------
def test_analyze_parameter_passes_in_and_required(
    analyzer: SchemaAnalyzer,
) -> None:
    p = analyzer.analyze_parameter(
        {
            "name": "limit",
            "in": "query",
            "required": True,
            "schema": {"type": "integer", "minimum": 1, "maximum": 100},
            "description": "page size",
        },
        {},
    )
    assert isinstance(p, ParameterSchema)
    assert p.name == "limit"
    assert p.in_ == "query"
    assert p.required is True
    assert p.schema_model.minimum == 1


# ---------------------------------------------------------------------------
# Extra: analyze_request_body picks first content type
# ---------------------------------------------------------------------------
def test_analyze_request_body_first_content_type(
    analyzer: SchemaAnalyzer,
) -> None:
    rb = analyzer.analyze_request_body(
        {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    }
                }
            },
        },
        {},
    )
    assert isinstance(rb, RequestSchema)
    assert rb.content_type == "application/json"
    assert rb.required is True
    assert rb.schema_model is not None
    assert "name" in rb.schema_model.properties


# ---------------------------------------------------------------------------
# Extra: analyze_response carries the schema
# ---------------------------------------------------------------------------
def test_analyze_response_carries_schema(analyzer: SchemaAnalyzer) -> None:
    r = analyzer.analyze_response(
        "201",
        {
            "description": "created",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"id": {"type": "string"}}}
                }
            },
        },
        {},
    )
    assert isinstance(r, ResponseSchema)
    assert r.status_code == "201"
    assert r.content_type == "application/json"
    assert r.schema_model is not None
    assert "id" in r.schema_model.properties