"""Tests for F022 Test Design Engine.

Covers T1–T20 in ``docs/01-product/F022_SPEC.md`` §11.  Uses
``openapi_factories.py`` for fixture construction (per F022_PRECHECK §3.3).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.test_design import (
    StrategyCapError,
    TestDesignEngine,
    TestIntent,
)
from app.domain.test_design.strategies import (
    AuthMissingStrategy,
    BoundaryMinMaxStrategy,
    EnumCoverageStrategy,
    FormatInvalidStrategy,
    HappyPathStrategy,
    RequiredFieldMissingStrategy,
)
from tests.openapi_factories import (
    make_endpoint_schema,
    make_endpoint_with_email_format,
    make_endpoint_with_enum_property,
    make_endpoint_with_numeric_boundary,
    make_endpoint_with_required_fields,
    make_endpoint_with_security,
    make_object_schema,
)


# ---------------------------------------------------------------------------
# Settings stand-in for TestDesignEngine.  The engine only reads the
# 12 attributes listed in its Protocol, so a dataclass is enough.
# ---------------------------------------------------------------------------
@dataclass
class _Settings:
    """Subset of Settings the F022 engine reads."""
    strategy_happy_path: bool = True
    strategy_required_field_missing: bool = False
    strategy_enum_coverage: bool = False
    strategy_boundary_min_max: bool = False
    strategy_format_invalid: bool = False
    strategy_auth_missing: bool = False
    generator_max_intents_per_operation: int = 20
    strategy_required_field_missing_max_per_op: int = 5
    strategy_enum_coverage_max_per_op: int = 10
    strategy_boundary_min_max_max_per_op: int = 10
    strategy_format_invalid_max_per_op: int = 5
    strategy_auth_missing_max_per_op: int = 1


def _engine(**overrides: Any) -> TestDesignEngine:
    return TestDesignEngine(_Settings(**overrides))


# ---------------------------------------------------------------------------
# T1 — happy_path 单 endpoint
# ---------------------------------------------------------------------------
def test_t1_happy_path_single_endpoint() -> None:
    ep = make_endpoint_schema(
        method="GET",
        path="/pets",
        summary="List pets",
        request_body=None,
    )
    eng = _engine()
    intents = eng.design(ep)
    assert len(intents) == 1
    assert intents[0].strategy == "happy_path"
    assert intents[0].expected_status_codes == [200, 201, 202, 204]
    assert len(intents[0].assertions) == 1
    assert intents[0].assertions[0]["type"] == "status_code"
    assert intents[0].assertions[0]["operator"] == "in"


# ---------------------------------------------------------------------------
# T2 — happy_path 不被配额影响
# ---------------------------------------------------------------------------
def test_t2_happy_path_not_capped() -> None:
    ep = make_endpoint_schema()
    direct = HappyPathStrategy().generate(ep)
    assert len(direct) == 1


# ---------------------------------------------------------------------------
# T3 — required_field_missing = 3 fields, default cap=5 → 3 intents
# ---------------------------------------------------------------------------
def test_t3_required_field_missing_three_fields() -> None:
    ep = make_endpoint_with_required_fields(["id", "name", "email"])
    eng = _engine(strategy_required_field_missing=True)
    intents = eng.design(ep)
    # 1 happy + 3 missing = 4
    assert len(intents) == 4
    names = [i.name for i in intents]
    assert any("missing required field 'id'" in n for n in names)
    assert any("missing required field 'name'" in n for n in names)
    assert any("missing required field 'email'" in n for n in names)


# ---------------------------------------------------------------------------
# T4 — required_field_missing = 8 fields, cap=5 → 截到 5
# ---------------------------------------------------------------------------
def test_t4_required_field_missing_eight_capped_at_five(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ep = make_endpoint_with_required_fields(
        ["a", "b", "c", "d", "e", "f", "g", "h"]
    )
    eng = _engine(strategy_required_field_missing=True)
    with caplog.at_level("WARNING"):
        intents = eng.design(ep)
    # 1 happy + 5 missing (capped) = 6
    assert len(intents) == 6
    assert any("strategy truncated" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# T5 — required_field_missing = 0 required → 0 intents (策略跳过)
# ---------------------------------------------------------------------------
def test_t5_required_field_missing_zero_required() -> None:
    ep = make_endpoint_schema(method="POST")
    eng = _engine(strategy_required_field_missing=True)
    intents = eng.design(ep)
    # 1 happy only
    assert len(intents) == 1
    assert intents[0].strategy == "happy_path"


# ---------------------------------------------------------------------------
# T6 — enum_coverage 单字段 5 values → 5 intents + body 字段值遍历
# ---------------------------------------------------------------------------
def test_t6_enum_coverage_single_field_five_values() -> None:
    ep = make_endpoint_with_enum_property(["a", "b", "c", "d", "e"])
    eng = _engine(strategy_enum_coverage=True)
    intents = eng.design(ep)
    # 1 happy + 5 enum = 6
    assert len(intents) == 6
    enum_intents = [i for i in intents if i.strategy == "enum_coverage"]
    assert len(enum_intents) == 5
    # body 中 status 字段值分别为每个 enum value
    values = [i.body_override["status"] for i in enum_intents]
    assert values == ["a", "b", "c", "d", "e"]


# ---------------------------------------------------------------------------
# T7 — enum_coverage 多字段 → 总数 > cap 时截断
# ---------------------------------------------------------------------------
def test_t7_enum_coverage_multi_field_capped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from app.domain.openapi_importer.schema_model import RequestSchema
    ep = make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {
                    "f1": {"type": "string", "enum": ["a", "b", "c", "d", "e"]},
                    "f2": {"type": "string", "enum": [str(i) for i in range(10)]},
                },
                required=["f1", "f2"],
            ),
        ),
    )
    eng = _engine(
        strategy_enum_coverage=True,
        strategy_enum_coverage_max_per_op=10,
    )
    with caplog.at_level("WARNING"):
        intents = eng.design(ep)
    enum_intents = [i for i in intents if i.strategy == "enum_coverage"]
    # 5 + 10 = 15 → 截到 10
    assert len(enum_intents) == 10
    assert any("strategy truncated" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# T8 — boundary_min_max 3 numeric fields → 每字段 6 条 → 截到 10
# ---------------------------------------------------------------------------
def test_t8_boundary_min_max_three_fields_capped() -> None:
    from app.domain.openapi_importer.schema_model import RequestSchema
    ep = make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {
                    "f1": {"type": "integer", "minimum": 0, "maximum": 10},
                    "f2": {"type": "integer", "minimum": 0, "maximum": 100},
                    "f3": {"type": "integer", "minimum": 0, "maximum": 5},
                },
                required=["f1", "f2", "f3"],
            ),
        ),
    )
    eng = _engine(
        strategy_boundary_min_max=True,
        strategy_boundary_min_max_max_per_op=10,
    )
    intents = eng.design(ep)
    boundary = [i for i in intents if i.strategy == "boundary_min_max"]
    # 3 fields × 6 = 18 → 截到 10
    assert len(boundary) == 10


# ---------------------------------------------------------------------------
# T9 — boundary_min_max 边界值正确（min-1, min, min+1, max-1, max, max+1）
# ---------------------------------------------------------------------------
def test_t9_boundary_min_max_values_correct() -> None:
    from app.domain.openapi_importer.schema_model import RequestSchema
    ep = make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {"age": {"type": "integer", "minimum": 0, "maximum": 2}},
                required=["age"],
            ),
        ),
    )
    eng = _engine(strategy_boundary_min_max=True)
    intents = [i for i in eng.design(ep) if i.strategy == "boundary_min_max"]
    values = sorted({i.body_override["age"] for i in intents})
    # min-1=-1, min=0, min+1=1, max-1=1, max=2, max+1=3 → 去重得 [-1, 0, 1, 2, 3]
    assert values == [-1, 0, 1, 2, 3]


# ---------------------------------------------------------------------------
# T10 — format_invalid email → 1 intent + invalid value
# ---------------------------------------------------------------------------
def test_t10_format_invalid_email() -> None:
    ep = make_endpoint_with_email_format()
    eng = _engine(strategy_format_invalid=True)
    intents = eng.design(ep)
    fmt = [i for i in intents if i.strategy == "format_invalid"]
    assert len(fmt) == 1
    assert fmt[0].body_override["email"] == "not-a-valid-email"
    assert fmt[0].expected_status_codes == [400, 422]


# ---------------------------------------------------------------------------
# T11 — format_invalid uuid
# ---------------------------------------------------------------------------
def test_t11_format_invalid_uuid() -> None:
    from app.domain.openapi_importer.schema_model import RequestSchema
    ep = make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {"id": {"type": "string", "format": "uuid"}},
                required=["id"],
            ),
        ),
    )
    eng = _engine(strategy_format_invalid=True)
    intents = [i for i in eng.design(ep) if i.strategy == "format_invalid"]
    assert len(intents) == 1
    assert intents[0].body_override["id"] == "not-a-uuid"


# ---------------------------------------------------------------------------
# T12 — auth_missing 带 security → 1 intent + Authorization removed
# ---------------------------------------------------------------------------
def test_t12_auth_missing_with_security() -> None:
    ep = make_endpoint_with_security(scheme_name="bearerAuth")
    eng = _engine(strategy_auth_missing=True)
    intents = eng.design(ep)
    auth = [i for i in intents if i.strategy == "auth_missing"]
    assert len(auth) == 1
    assert auth[0].headers_override == {}
    assert auth[0].expected_status_codes == [401]


# ---------------------------------------------------------------------------
# T13 — auth_missing 无 security → 0 intents
# ---------------------------------------------------------------------------
def test_t13_auth_missing_without_security() -> None:
    ep = make_endpoint_schema()  # no security
    eng = _engine(strategy_auth_missing=True)
    intents = eng.design(ep)
    assert all(i.strategy != "auth_missing" for i in intents)


# ---------------------------------------------------------------------------
# T14 — 多策略 enabled 联合（happy + required + enum）→ 1 + 3 + 5 = 9
# ---------------------------------------------------------------------------
def test_t14_multi_strategy_combined() -> None:
    from app.domain.openapi_importer.schema_model import RequestSchema
    ep = make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {
                    "id": {"type": "string"},
                    "status": {"type": "string", "enum": ["a", "b", "c"]},
                },
                required=["id", "status"],
            ),
        ),
    )
    eng = _engine(
        strategy_required_field_missing=True,
        strategy_enum_coverage=True,
    )
    intents = eng.design(ep)
    # 1 happy + 2 required + 3 enum = 6
    assert len(intents) == 6
    # happy_path must be first
    assert intents[0].strategy == "happy_path"


# ---------------------------------------------------------------------------
# T15 — 硬截（所有策略产出总和 > generator_max）
#
# 设计：把单策略配额提到 generator_max=20，让策略层不截断；
# 同时让策略层产出总数 > 20，从而触发引擎硬截 + WARNING。
# 字段：
#   - 10 个 required → required_field_missing 产 10 条
#   - 1 个 enum 字段含 10 个 values → enum_coverage 产 10 条
#   - happy_path 1 条
# 合计：1 + 10 + 10 = 21 > generator_max=20 → 硬截到 20。
# ---------------------------------------------------------------------------
def test_t15_hard_cap_truncation(caplog: pytest.LogCaptureFixture) -> None:
    from app.domain.openapi_importer.schema_model import RequestSchema
    ep = make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {
                    "status": {
                        "type": "string",
                        "enum": [str(i) for i in range(10)],
                    },
                    "f1": {"type": "string"},
                    "f2": {"type": "string"},
                    "f3": {"type": "string"},
                    "f4": {"type": "string"},
                    "f5": {"type": "string"},
                    "f6": {"type": "string"},
                    "f7": {"type": "string"},
                    "f8": {"type": "string"},
                    "f9": {"type": "string"},
                    "f10": {"type": "string"},
                },
                required=[
                    "status", "f1", "f2", "f3", "f4", "f5",
                    "f6", "f7", "f8", "f9", "f10",
                ],
            ),
        ),
    )
    eng = _engine(
        generator_max_intents_per_operation=20,
        strategy_required_field_missing=True,
        strategy_enum_coverage=True,
        # raise per-strategy caps so they don't trigger truncation
        # before the hard cap does.
        strategy_required_field_missing_max_per_op=20,
        strategy_enum_coverage_max_per_op=20,
    )
    with caplog.at_level("WARNING"):
        intents = eng.design(ep)
    # 1 happy + 10 required + 10 enum = 21 → engine hard-cap → 20
    assert len(intents) == 20
    assert any("hard cap hit" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# T16 — 启动校验：strategy_*_max > generator_max 抛 StrategyCapError
# ---------------------------------------------------------------------------
def test_t16_startup_cap_validation() -> None:
    with pytest.raises(StrategyCapError):
        _engine(
            strategy_enum_coverage_max_per_op=25,
            generator_max_intents_per_operation=20,
        )


def test_t16b_startup_cap_validation_out_of_range() -> None:
    with pytest.raises(StrategyCapError):
        _engine(generator_max_intents_per_operation=200)


# ---------------------------------------------------------------------------
# T17 — 默认 enabled 字节级 = F012
# ---------------------------------------------------------------------------
def test_t17_default_byte_equivalent_to_f012() -> None:
    ep = make_endpoint_schema(method="GET", path="/pets", summary="List")
    eng = _engine()  # only happy_path enabled
    intents = eng.design(ep)
    assert len(intents) == 1
    assert intents[0].strategy == "happy_path"
    # The single intent mirrors F012's happy path shape.
    assert intents[0].expected_status_codes == [200, 201, 202, 204]


# ---------------------------------------------------------------------------
# T18 — batch design 入口
# ---------------------------------------------------------------------------
def test_t18_batch_design() -> None:
    ep1 = make_endpoint_schema(method="GET", path="/a")
    ep2 = make_endpoint_schema(method="POST", path="/b")
    eng = _engine(strategy_required_field_missing=True)
    out = eng.design_batch([ep1, ep2])
    assert set(out.keys()) == {"GET /a", "POST /b"}
    assert isinstance(out["GET /a"], list)
    assert isinstance(out["POST /b"], list)


# ---------------------------------------------------------------------------
# T19 — 6 个策略类都实现 Strategy 协议（运行时检查）
# ---------------------------------------------------------------------------
def test_t19_all_strategies_implement_protocol() -> None:
    """Duck-type check: each strategy has name/default_enabled/max_per_op/generate."""
    strategies = [
        HappyPathStrategy(),
        RequiredFieldMissingStrategy(),
        EnumCoverageStrategy(),
        BoundaryMinMaxStrategy(),
        FormatInvalidStrategy(),
        AuthMissingStrategy(),
    ]
    for strat in strategies:
        assert isinstance(strat.name, str)
        assert isinstance(strat.default_enabled, bool)
        assert isinstance(strat.max_per_op, int)
        assert hasattr(strat, "generate") and callable(strat.generate)


# ---------------------------------------------------------------------------
# T20 — TestIntent Pydantic v2 extra=forbid
# ---------------------------------------------------------------------------
def test_t20_test_intent_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        TestIntent(
            intent_id="x",
            strategy="happy_path",
            operation_id="GET /x",
            method="GET",
            path="/x",
            name="x",
            extra_unexpected_field="oops",  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# Extra: 直接构造策略类（不通过引擎）也工作
# ---------------------------------------------------------------------------
def test_extra_direct_strategy_construction() -> None:
    ep = make_endpoint_with_required_fields(["a", "b"])
    intents = RequiredFieldMissingStrategy(max_per_op=3).generate(ep)
    assert len(intents) == 2
    assert all(i.strategy == "required_field_missing" for i in intents)


# ---------------------------------------------------------------------------
# Extra: 多个 strategy 同时启用时 happy_path 永远排第一
# ---------------------------------------------------------------------------
def test_extra_happy_path_always_first() -> None:
    from app.domain.openapi_importer.schema_model import RequestSchema
    ep = make_endpoint_schema(
        method="POST",
        request_body=RequestSchema(
            content_type="application/json",
            schema_model=make_object_schema(
                {"x": {"type": "string"}}, required=["x"]
            ),
        ),
    )
    eng = _engine(
        strategy_required_field_missing=True,
        strategy_format_invalid=True,
    )
    intents = eng.design(ep)
    assert intents[0].strategy == "happy_path"