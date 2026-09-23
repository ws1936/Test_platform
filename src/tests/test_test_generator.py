"""Unit tests for F023 TestGenerator (pure function).

Covers FT-U01–U13 in ``docs/01-product/F023_SPEC.md`` §10.1.

The TestGenerator consumes a F022 ``TestIntent`` (plus F012 ``Operation``
for default request fields and F021 ``EndpointSchema`` for response-
schema metadata) and emits a F007 ``TestCaseCreateRequest``. No DB, no
HTTP coupling.
"""

from __future__ import annotations

import copy

import pytest

from app.domain.openapi_importer.parser import Operation
from app.domain.openapi_importer.schema_model import (EndpointSchema,
                                                      ParameterSchema,
                                                      RequestSchema,
                                                      ResponseSchema,
                                                      SchemaModel,
                                                      SecurityRequirement)
from app.domain.test_case.schema import TestCaseCreateRequest
from app.domain.test_design.schema import TestIntent
from app.domain.test_generator import TestGenerator
from tests.openapi_factories import (make_endpoint_schema,
                                     make_endpoint_with_email_format,
                                     make_endpoint_with_enum_property,
                                     make_endpoint_with_numeric_boundary,
                                     make_endpoint_with_required_fields,
                                     make_endpoint_with_security,
                                     make_object_schema)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _op(
    method: str = "POST",
    path: str = "/pets",
    name: str = "Create pet",
    body: object = ...,
    body_type: str = "none",
    headers: dict | None = None,
    query: dict | None = None,
) -> Operation:
    """Build a minimal F012 ``Operation`` for unit tests."""
    return Operation(
        operation_id=f"{method} {path}",
        method=method,
        path=path,
        name=name,
        request_headers=dict(headers or {}),
        request_query=dict(query or {}),
        request_body=(None if body is ... else copy.deepcopy(body)),
        request_body_type=body_type,
    )


def _gen() -> TestGenerator:
    return TestGenerator()


# ---------------------------------------------------------------------------
# FT-U01 — happy_path 字节级等价 F012
# ---------------------------------------------------------------------------
def test_ft_u01_happy_path_byte_equivalent_to_f012() -> None:
    """``intent_to_request(happy_path)`` produces the same shape as
    F012's ``create_req = TestCaseCreateRequest(...)`` factory in
    ``OpenApiImportService.import_from_preview``.
    """
    intent = TestIntent(
        intent_id="i-001",
        strategy="happy_path",
        operation_id="POST /pets",
        method="POST",
        path="/pets",
        name="Create pet: happy path",
        body_override={"name": "fluffy"},
        body_type_override="json",
        assertions=[
            {"type": "status_code", "operator": "in", "expected": [200, 201, 202, 204]},
        ],
        expected_status_codes=[200, 201, 202, 204],
        expected_status_mode="any_of",
    )
    op = _op(
        method="POST",
        path="/pets",
        name="Create pet",
        body={"name": "fluffy"},
        body_type="json",
    )
    endpoint = make_endpoint_schema(method="POST", path="/pets")
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    # Byte-equivalent assertion list with F012's exact 1-element shape.
    assert isinstance(req, TestCaseCreateRequest)
    assert req.method == "POST"
    assert req.path == "/pets"
    assert req.body == {"name": "fluffy"}
    assert req.body_type == "json"
    assert req.assertions == [
        {"type": "status_code", "operator": "in", "expected": [200, 201, 202, 204]},
    ]


# ---------------------------------------------------------------------------
# FT-U02 — required_field_missing body_override 应用
# ---------------------------------------------------------------------------
def test_ft_u02_required_field_missing_body_override_applied() -> None:
    """F022's required_field_missing strategy produces a body_override
    with one required field set to None; the generator must pass that
    through and add the status_code in [400, 422] assertion.
    """
    intent = TestIntent(
        intent_id="i-002",
        strategy="required_field_missing",
        operation_id="POST /pets",
        method="POST",
        path="/pets",
        name="Create pet: missing required field 'name'",
        body_override={"name": None, "age": 3},
        body_type_override="json",
        assertions=[
            {"type": "status_code", "operator": "in", "expected": [400, 422]},
        ],
        expected_status_codes=[400, 422],
        expected_status_mode="any_of",
    )
    op = _op(
        method="POST",
        path="/pets",
        name="Create pet",
        body={"name": "fluffy", "age": 3},
        body_type="json",
    )
    endpoint = make_endpoint_schema(method="POST", path="/pets")
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    assert req.body == {"name": None, "age": 3}
    # Assertions must include status_code [400,422] from intent.assertions.
    assert {
        "type": "status_code",
        "operator": "in",
        "expected": [400, 422],
    } in req.assertions


# ---------------------------------------------------------------------------
# FT-U03 — enum_coverage body 单字段替换
# ---------------------------------------------------------------------------
def test_ft_u03_enum_coverage_body_single_field_swap() -> None:
    """F022 enum_coverage replaces a single field's value with one enum
    entry; all other fields must remain untouched."""
    intent = TestIntent(
        intent_id="i-003",
        strategy="enum_coverage",
        operation_id="POST /pets",
        method="POST",
        path="/pets",
        name="Create pet: enum 'status' = 'available'",
        body_override={"name": "fluffy", "status": "available"},
        body_type_override="json",
        assertions=[{"type": "status_code", "operator": "in", "expected": [200, 201]}],
        expected_status_codes=[200, 201],
        expected_status_mode="any_of",
    )
    op = _op(
        method="POST",
        path="/pets",
        name="Create pet",
        body={"name": "fluffy", "status": "pending"},
        body_type="json",
    )
    endpoint = make_endpoint_schema(method="POST", path="/pets")
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    assert req.body == {"name": "fluffy", "status": "available"}
    # ``status`` field was swapped; ``name`` preserved from op defaults.


# ---------------------------------------------------------------------------
# FT-U04 — boundary_min_max body 单数值替换
# ---------------------------------------------------------------------------
def test_ft_u04_boundary_min_max_body_single_value() -> None:
    """boundary_min_max produces 6 candidate bodies (min-1/min/min+1/
    max-1/max/max+1); each generator invocation receives one body."""
    for val in (0, 1, 5, 17, 18, 99):
        intent = TestIntent(
            intent_id=f"i-004-{val}",
            strategy="boundary_min_max",
            operation_id="POST /pets",
            method="POST",
            path="/pets",
            name=f"boundary age={val}",
            body_override={"age": val},
            body_type_override="json",
            assertions=[
                {"type": "status_code", "operator": "in", "expected": [200, 201]}
            ],
            expected_status_codes=[200, 201],
            expected_status_mode="any_of",
        )
        op = _op(
            method="POST",
            path="/pets",
            name="Create pet",
            body={"age": 18},
            body_type="json",
        )
        endpoint = make_endpoint_schema(method="POST", path="/pets")
        req = _gen().intent_to_request(
            intent=intent,
            operation=op,
            endpoint=endpoint,
        )
        assert req.body == {"age": val}


# ---------------------------------------------------------------------------
# FT-U05 — format_invalid body 字段填非法值
# ---------------------------------------------------------------------------
def test_ft_u05_format_invalid_email_field() -> None:
    intent = TestIntent(
        intent_id="i-005",
        strategy="format_invalid",
        operation_id="POST /users",
        method="POST",
        path="/users",
        name="invalid format on email",
        body_override={"email": "not-a-valid-email"},
        body_type_override="json",
        assertions=[{"type": "status_code", "operator": "in", "expected": [400, 422]}],
        expected_status_codes=[400, 422],
        expected_status_mode="any_of",
    )
    op = _op(
        method="POST",
        path="/users",
        name="Create user",
        body={"email": "valid@example.com"},
        body_type="json",
    )
    endpoint = make_endpoint_with_email_format()
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    assert req.body == {"email": "not-a-valid-email"}


# ---------------------------------------------------------------------------
# FT-U06 — auth_missing Authorization 移除
# ---------------------------------------------------------------------------
def test_ft_u06_auth_missing_strips_authorization() -> None:
    """auth_missing strategy: regardless of intent.headers_override, the
    generator must NOT carry an Authorization header."""
    intent = TestIntent(
        intent_id="i-006",
        strategy="auth_missing",
        operation_id="GET /pets",
        method="GET",
        path="/pets",
        name="missing auth",
        headers_override=None,
        query_override=None,
        body_override=None,
        body_type_override=None,
        assertions=[{"type": "status_code", "operator": "in", "expected": [401]}],
        expected_status_codes=[401],
        expected_status_mode="any_of",
    )
    op = _op(
        method="GET",
        path="/pets",
        name="List pets",
        headers={"Authorization": "Bearer abc.def.ghi"},
    )
    endpoint = make_endpoint_with_security()
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    assert req.headers is None or "Authorization" not in req.headers
    assert req.assertions == [
        {"type": "status_code", "operator": "in", "expected": [401]},
    ]


# ---------------------------------------------------------------------------
# FT-U07 — name 长度截断
# ---------------------------------------------------------------------------
def test_ft_u07_name_truncated_to_200() -> None:
    """Defensive truncation: TestIntent.name is already constrained to
    max_length=200 at the F022 schema layer, so a 200-char intent name
    must pass through unchanged and the generator must NOT accidentally
    inflate it past 200.
    """
    name_200 = "x" * 200
    intent = TestIntent(
        intent_id="i-007",
        strategy="happy_path",
        operation_id="POST /x",
        method="POST",
        path="/x",
        name=name_200,
        body_override=None,
        body_type_override=None,
        assertions=[{"type": "status_code", "operator": "in", "expected": [200]}],
        expected_status_codes=[200],
        expected_status_mode="any_of",
    )
    op = _op(method="POST", path="/x", name="x")
    endpoint = make_endpoint_schema(method="POST", path="/x")
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    assert len(req.name) == 200
    assert req.name == "x" * 200


# ---------------------------------------------------------------------------
# FT-U08 — body_type_override 切换
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("body_type", ["none", "json", "form", "raw"])
def test_ft_u08_body_type_override_switched(body_type: str) -> None:
    intent = TestIntent(
        intent_id=f"i-008-{body_type}",
        strategy="happy_path",
        operation_id="POST /x",
        method="POST",
        path="/x",
        name="happy",
        body_override=None,
        body_type_override=body_type,
        assertions=[{"type": "status_code", "operator": "in", "expected": [200]}],
        expected_status_codes=[200],
        expected_status_mode="any_of",
    )
    # The Operation's request_body_type is "json" — the override should
    # take precedence regardless.
    op = _op(method="POST", path="/x", name="x", body_type="json")
    endpoint = make_endpoint_schema(method="POST", path="/x")
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    assert req.body_type == body_type


# ---------------------------------------------------------------------------
# FT-U09 — assertion 合并去重
# ---------------------------------------------------------------------------
def test_ft_u09_assertion_merge_dedupe() -> None:
    """Two identical status_code [200,201,202,204] assertions (one from
    intent.expected_status_codes and one from intent.assertions) must
    collapse to one after dedupe.
    """
    dup_assertion = {
        "type": "status_code",
        "operator": "in",
        "expected": [200, 201, 202, 204],
    }
    intent = TestIntent(
        intent_id="i-009",
        strategy="happy_path",
        operation_id="POST /pets",
        method="POST",
        path="/pets",
        name="happy",
        body_override={"name": "f"},
        body_type_override="json",
        assertions=[dup_assertion],
        expected_status_codes=[200, 201, 202, 204],
        expected_status_mode="any_of",
    )
    op = _op(
        method="POST",
        path="/pets",
        name="Create pet",
        body={"name": "f"},
        body_type="json",
    )
    endpoint = make_endpoint_schema(method="POST", path="/pets")
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    # Exactly one status_code assertion (no duplicates).
    sc_asserts = [a for a in req.assertions if a.get("type") == "status_code"]
    assert len(sc_asserts) == 1
    assert sc_asserts[0]["expected"] == [200, 201, 202, 204]


# ---------------------------------------------------------------------------
# FT-U10 — json_path 自动生成（响应 schema required）
# ---------------------------------------------------------------------------
def test_ft_u10_json_path_auto_generated_from_required() -> None:
    """Given a happy_path intent whose endpoint declares a 200 response
    with required fields ["id", "name"], the generator must emit two
    ``json_path $.<field> exists`` assertions.
    """
    resp_schema = make_object_schema(
        properties={
            "id": {"type": "string"},
            "name": {"type": "string"},
            "tag": {"type": "string"},
        },
        required=["id", "name"],
    )
    endpoint = EndpointSchema(
        method="POST",
        path="/pets",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=resp_schema,
            required=True,
        ),
        responses=[
            ResponseSchema(
                status_code="200",
                content_type="application/json",
                schema_model=resp_schema,
            )
        ],
    )
    intent = TestIntent(
        intent_id="i-010",
        strategy="happy_path",
        operation_id="POST /pets",
        method="POST",
        path="/pets",
        name="happy",
        body_override={"id": None, "name": "fluffy"},
        body_type_override="json",
        assertions=[
            {"type": "status_code", "operator": "in", "expected": [200, 201, 202, 204]}
        ],
        expected_status_codes=[200, 201, 202, 204],
        expected_status_mode="any_of",
    )
    op = _op(
        method="POST",
        path="/pets",
        name="Create pet",
        body={"id": None, "name": "fluffy"},
        body_type="json",
    )
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    jp_asserts = [a for a in req.assertions if a.get("type") == "json_path"]
    paths = {a["expected"] for a in jp_asserts}
    assert "$.id" in paths
    assert "$.name" in paths
    assert "$.tag" not in paths  # not required → not auto-asserted


# ---------------------------------------------------------------------------
# FT-U11 — json_path 不生成（响应 schema 缺失）
# ---------------------------------------------------------------------------
def test_ft_u11_json_path_silently_skipped_when_no_response_schema() -> None:
    """ADR-009 decision 5: silent skip when response schema absent; only
    status_code assertions remain."""
    endpoint = EndpointSchema(  # no ``responses`` at all
        method="POST",
        path="/pets",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                properties={"name": {"type": "string"}},
                required=["name"],
            ),
            required=True,
        ),
        responses=[],
    )
    intent = TestIntent(
        intent_id="i-011",
        strategy="happy_path",
        operation_id="POST /pets",
        method="POST",
        path="/pets",
        name="happy",
        body_override={"name": "f"},
        body_type_override="json",
        assertions=[
            {"type": "status_code", "operator": "in", "expected": [200, 201, 202, 204]}
        ],
        expected_status_codes=[200, 201, 202, 204],
        expected_status_mode="any_of",
    )
    op = _op(
        method="POST",
        path="/pets",
        name="Create pet",
        body={"name": "f"},
        body_type="json",
    )
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    # No json_path assertions; only the single status_code remains.
    assert all(a.get("type") != "json_path" for a in req.assertions)


# ---------------------------------------------------------------------------
# FT-U12 — header 自动生成（content-type）
# ---------------------------------------------------------------------------
def test_ft_u12_header_auto_generated_content_type() -> None:
    endpoint = EndpointSchema(
        method="POST",
        path="/pets",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                properties={"name": {"type": "string"}},
                required=["name"],
            ),
            required=True,
        ),
        responses=[
            ResponseSchema(
                status_code="200",
                content_type="application/json",
                schema_model=make_object_schema(
                    properties={"id": {"type": "string"}},
                    required=["id"],
                ),
            )
        ],
    )
    intent = TestIntent(
        intent_id="i-012",
        strategy="happy_path",
        operation_id="POST /pets",
        method="POST",
        path="/pets",
        name="happy",
        body_override={"name": "f"},
        body_type_override="json",
        assertions=[{"type": "status_code", "operator": "in", "expected": [200]}],
        expected_status_codes=[200],
        expected_status_mode="any_of",
    )
    op = _op(
        method="POST",
        path="/pets",
        name="Create pet",
        body={"name": "f"},
        body_type="json",
    )
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    h_asserts = [a for a in req.assertions if a.get("type") == "header"]
    assert any(a["expected"] == "Content-Type" for a in h_asserts)


# ---------------------------------------------------------------------------
# FT-U13 — 多 intent 顺序保留
# ---------------------------------------------------------------------------
def test_ft_u13_multiple_intents_order_preserved() -> None:
    """intents_to_requests preserves F022's priority order: happy_path
    first, then required_field_missing etc.
    """
    op = _op(
        method="POST",
        path="/pets",
        name="Create pet",
        body={"name": "f", "status": "available"},
        body_type="json",
    )
    endpoint = make_endpoint_schema(method="POST", path="/pets")
    intents = [
        TestIntent(
            intent_id="hp",
            strategy="happy_path",
            operation_id="POST /pets",
            method="POST",
            path="/pets",
            name="happy",
            body_override={"name": "f", "status": "available"},
            body_type_override="json",
            assertions=[{"type": "status_code", "operator": "in", "expected": [200]}],
            expected_status_codes=[200],
            expected_status_mode="any_of",
        ),
        TestIntent(
            intent_id="rfm",
            strategy="required_field_missing",
            operation_id="POST /pets",
            method="POST",
            path="/pets",
            name="missing 'name'",
            body_override={"name": None, "status": "available"},
            body_type_override="json",
            assertions=[
                {"type": "status_code", "operator": "in", "expected": [400, 422]}
            ],
            expected_status_codes=[400, 422],
            expected_status_mode="any_of",
        ),
    ]
    reqs = _gen().intents_to_requests(
        intents=intents,
        operation=op,
        endpoint=endpoint,
    )
    assert len(reqs) == 2
    assert reqs[0].name == "happy"
    assert reqs[1].name == "missing 'name'"


# ---------------------------------------------------------------------------
# Defensive test — auth_missing still strips lowercase Authorization
# ---------------------------------------------------------------------------
def test_ft_u06b_auth_missing_strips_lowercase_authorization() -> None:
    intent = TestIntent(
        intent_id="i-006b",
        strategy="auth_missing",
        operation_id="GET /pets",
        method="GET",
        path="/pets",
        name="missing auth",
        headers_override=None,
        query_override=None,
        body_override=None,
        body_type_override=None,
        assertions=[{"type": "status_code", "operator": "in", "expected": [401]}],
        expected_status_codes=[401],
        expected_status_mode="any_of",
    )
    op = _op(
        method="GET",
        path="/pets",
        name="List pets",
        headers={"authorization": "Bearer abc"},
    )
    endpoint = make_endpoint_with_security()
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    assert req.headers is None or "authorization" not in req.headers
    assert req.headers is None or "Authorization" not in req.headers


# ---------------------------------------------------------------------------
# Defensive test — non-happy_path intent skips auto-assertions
# ---------------------------------------------------------------------------
def test_ft_u11b_non_happy_path_skips_auto_assertions() -> None:
    """required_field_missing must NOT auto-generate json_path / header
    assertions (auto-assertions are happy_path-only per SPEC §3.2)."""
    resp_schema = make_object_schema(
        properties={"id": {"type": "string"}},
        required=["id"],
    )
    endpoint = EndpointSchema(
        method="POST",
        path="/pets",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=resp_schema,
            required=True,
        ),
        responses=[
            ResponseSchema(
                status_code="200",
                content_type="application/json",
                schema_model=resp_schema,
            )
        ],
    )
    intent = TestIntent(
        intent_id="rfm-no-auto",
        strategy="required_field_missing",
        operation_id="POST /pets",
        method="POST",
        path="/pets",
        name="missing id",
        body_override={"id": None},
        body_type_override="json",
        assertions=[{"type": "status_code", "operator": "in", "expected": [400, 422]}],
        expected_status_codes=[400, 422],
        expected_status_mode="any_of",
    )
    op = _op(
        method="POST",
        path="/pets",
        name="Create pet",
        body={"id": "abc"},
        body_type="json",
    )
    req = _gen().intent_to_request(
        intent=intent,
        operation=op,
        endpoint=endpoint,
    )
    assert all(a.get("type") != "json_path" for a in req.assertions)
    assert all(a.get("type") != "header" for a in req.assertions)
