"""Unit tests for the F009 Assertion Engine.

The engine is a pure-function library; every test feeds a hand-built
``_FakeResponse`` instead of touching the network. Coverage target
≥ 80% per AI_RULES §12 ("断言引擎" must be重点测试).

Sections
--------
1. Module surface (exports)
2. ``AssertionRule`` validation (errors raised at construction time)
3. ``parse_assertion`` round-trip
4. ``status_code`` assertions
5. ``json_path`` assertions (deep paths, brackets, missing keys)
6. ``header`` assertions (case-insensitive lookup, existence)
7. ``response_time`` assertions (seconds float)
8. ``body_contains`` assertions (case sensitivity, list expected)
9. ``evaluate_all`` (multiple rules, empty list, mixed types)
10. F008 integration — ``${var}`` placeholders in ``expected``
11. Error-code mapping (31003 / 31004 / 31005)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Mapping, Optional

import pytest

from app.domain.test_engine import (
    ALLOWED_OPERATORS,
    ALLOWED_TYPES,
    AssertionEngineError,
    AssertionResult,
    AssertionRule,
    evaluate,
    evaluate_all,
    parse_assertion,
)
from app.domain.test_engine.exceptions import (
    AssertionConfigError,
    UnsupportedAssertionOperatorError,
    UnsupportedAssertionTypeError,
)


# === Test helpers ===========================================================


@dataclass
class _FakeResponse:
    """Duck-typed response that satisfies what the engine reads.

    Production uses ``httpx.Response``; tests use this so we never
    touch the network. All fields are keyword-only to keep the
    call-site readable.
    """

    status_code: int = 200
    json_data: Any = None
    text: str = ""
    headers: Mapping[str, str] = field(default_factory=dict)
    elapsed_seconds: float = 0.0

    def json(self) -> Any:
        if self.json_data is not None:
            return self.json_data
        if self.text:
            return json.loads(self.text)
        raise ValueError("no JSON body")

    @property
    def elapsed(self) -> timedelta:
        return timedelta(seconds=self.elapsed_seconds)


def _resp(**kwargs: Any) -> _FakeResponse:
    """Shorthand to build a ``_FakeResponse`` for one assertion."""
    return _FakeResponse(**kwargs)


# === 1. Module surface =======================================================


def test_module_exposes_expected_symbols():
    """Public surface includes the types and functions the engine needs."""
    # Re-import to assert names; the bare ``from … import *`` above
    # already exercises the import path.
    from app.domain.test_engine import (  # noqa: F401  (re-import)
        AssertionOperator,
        AssertionResult,
        AssertionRule,
        AssertionType,
        evaluate,
        evaluate_all,
        parse_assertion,
    )


def test_allowed_types_is_frozenset_of_five():
    assert ALLOWED_TYPES == frozenset(
        {"status_code", "json_path", "header", "response_time", "body_contains"}
    )


def test_allowed_operators_is_frozenset_of_twelve():
    assert ALLOWED_OPERATORS == frozenset(
        {
            "eq", "ne", "gt", "lt", "ge", "le",
            "contains", "not_contains",
            "in", "not_in",
            "exists", "not_exists",
        }
    )


# === 2. AssertionRule validation ============================================


def test_assertion_rule_validates_status_code_eq():
    rule = AssertionRule(type="status_code", operator="eq", expected=200)
    assert rule.type == "status_code"
    assert rule.operator == "eq"


def test_assertion_rule_rejects_unknown_type():
    with pytest.raises(UnsupportedAssertionTypeError) as exc_info:
        AssertionRule(type="regex_match", operator="eq", expected=".*")
    assert "regex_match" in str(exc_info.value)


def test_assertion_rule_rejects_operator_not_allowed_for_type():
    """``header`` does not support ``gt``."""
    with pytest.raises(UnsupportedAssertionOperatorError) as exc_info:
        AssertionRule(
            type="header", operator="gt", expected=10, header_name="X-Foo"
        )
    assert "gt" in str(exc_info.value)
    assert "header" in str(exc_info.value)


def test_assertion_rule_requires_expected_for_non_existence_ops():
    with pytest.raises(AssertionConfigError) as exc_info:
        AssertionRule(type="status_code", operator="eq", expected=None)
    assert "expected" in str(exc_info.value)


def test_assertion_rule_allows_missing_expected_for_exists():
    rule = AssertionRule(type="json_path", operator="exists", path="user.id")
    assert rule.expected is None


def test_assertion_rule_allows_missing_expected_for_not_exists():
    rule = AssertionRule(
        type="header", operator="not_exists", header_name="X-Missing"
    )
    assert rule.expected is None


def test_assertion_rule_requires_path_for_json_path():
    with pytest.raises(AssertionConfigError):
        AssertionRule(type="json_path", operator="eq", expected=42)


def test_assertion_rule_rejects_path_on_non_json_path():
    with pytest.raises(AssertionConfigError):
        AssertionRule(
            type="status_code", operator="eq", expected=200, path="ignored"
        )


def test_assertion_rule_requires_header_name_for_header():
    with pytest.raises(AssertionConfigError):
        AssertionRule(type="header", operator="exists")


def test_assertion_rule_rejects_header_name_on_non_header():
    with pytest.raises(AssertionConfigError):
        AssertionRule(
            type="status_code", operator="eq", expected=200, header_name="X"
        )


def test_assertion_rule_rejects_case_insensitive_on_non_body_contains():
    with pytest.raises(AssertionConfigError):
        AssertionRule(
            type="status_code",
            operator="eq",
            expected=200,
            case_insensitive=True,
        )


# === 3. parse_assertion round-trip =========================================


def test_parse_assertion_minimal_dict():
    rule = parse_assertion({"type": "status_code", "operator": "eq", "expected": 200})
    assert rule.type == "status_code"
    assert rule.operator == "eq"
    assert rule.expected == 200


def test_parse_assertion_missing_type_raises_key_error():
    with pytest.raises(KeyError):
        parse_assertion({"operator": "eq", "expected": 1})


def test_parse_assertion_missing_operator_raises_key_error():
    with pytest.raises(KeyError):
        parse_assertion({"type": "status_code", "expected": 1})


def test_parse_assertion_invalid_type_raises_unsupported_type():
    with pytest.raises(UnsupportedAssertionTypeError):
        parse_assertion({"type": "nope", "operator": "eq", "expected": 1})


def test_parse_assertion_invalid_operator_raises_unsupported_operator():
    with pytest.raises(UnsupportedAssertionOperatorError):
        parse_assertion(
            {"type": "response_time", "operator": "contains", "expected": "x"}
        )


def test_parse_assertion_propagates_assertion_config_error():
    """Missing ``path`` for ``json_path`` becomes ``AssertionConfigError``."""
    with pytest.raises(AssertionConfigError):
        parse_assertion({"type": "json_path", "operator": "eq", "expected": 1})


def test_parse_assertion_defaults_case_insensitive_to_false():
    rule = parse_assertion(
        {"type": "body_contains", "operator": "contains", "expected": "x"}
    )
    assert rule.case_insensitive is False


def test_parse_assertion_accepts_case_insensitive_true_for_body_contains():
    rule = parse_assertion(
        {
            "type": "body_contains",
            "operator": "contains",
            "expected": "x",
            "case_insensitive": True,
        }
    )
    assert rule.case_insensitive is True


# === 4. status_code assertions =============================================


def test_status_code_eq_passes():
    rule = parse_assertion({"type": "status_code", "operator": "eq", "expected": 200})
    result = evaluate(rule, _resp(status_code=200))
    assert result.passed is True
    assert result.actual == 200


def test_status_code_eq_fails():
    rule = parse_assertion({"type": "status_code", "operator": "eq", "expected": 200})
    result = evaluate(rule, _resp(status_code=404))
    assert result.passed is False
    assert result.actual == 404
    assert "actual=404" in result.message


def test_status_code_ne_passes_when_different():
    rule = parse_assertion({"type": "status_code", "operator": "ne", "expected": 200})
    assert evaluate(rule, _resp(status_code=500)).passed is True


def test_status_code_ge_passes_for_5xx():
    rule = parse_assertion({"type": "status_code", "operator": "ge", "expected": 500})
    assert evaluate(rule, _resp(status_code=503)).passed is True


def test_status_code_lt_fails_for_4xx_vs_300():
    """``400 lt 300`` is false — 400 is not less than 300."""
    rule = parse_assertion({"type": "status_code", "operator": "lt", "expected": 300})
    assert evaluate(rule, _resp(status_code=400)).passed is False


def test_status_code_in_passes():
    rule = parse_assertion(
        {"type": "status_code", "operator": "in", "expected": [200, 201, 204]}
    )
    assert evaluate(rule, _resp(status_code=201)).passed is True


def test_status_code_in_fails():
    rule = parse_assertion(
        {"type": "status_code", "operator": "in", "expected": [200, 201]}
    )
    assert evaluate(rule, _resp(status_code=404)).passed is False


def test_status_code_not_in_passes():
    rule = parse_assertion(
        {"type": "status_code", "operator": "not_in", "expected": [500, 502, 503]}
    )
    assert evaluate(rule, _resp(status_code=200)).passed is True


def test_status_code_not_in_fails():
    rule = parse_assertion(
        {"type": "status_code", "operator": "not_in", "expected": [200]}
    )
    assert evaluate(rule, _resp(status_code=200)).passed is False


# === 5. json_path assertions ===============================================


def test_json_path_eq_simple_key():
    rule = parse_assertion(
        {"type": "json_path", "operator": "eq", "path": "id", "expected": 42}
    )
    result = evaluate(rule, _resp(json_data={"id": 42}))
    assert result.passed is True


def test_json_path_eq_nested_path():
    rule = parse_assertion(
        {
            "type": "json_path",
            "operator": "eq",
            "path": "user.address.city",
            "expected": "Shanghai",
        }
    )
    result = evaluate(
        rule,
        _resp(json_data={"user": {"address": {"city": "Shanghai"}}}),
    )
    assert result.passed is True


def test_json_path_eq_list_index_dotted():
    rule = parse_assertion(
        {
            "type": "json_path",
            "operator": "eq",
            "path": "items.0.name",
            "expected": "first",
        }
    )
    assert evaluate(
        rule,
        _resp(json_data={"items": [{"name": "first"}, {"name": "second"}]}),
    ).passed is True


def test_json_path_eq_list_index_brackets():
    rule = parse_assertion(
        {
            "type": "json_path",
            "operator": "eq",
            "path": "items[1].name",
            "expected": "second",
        }
    )
    assert evaluate(
        rule,
        _resp(json_data={"items": [{"name": "first"}, {"name": "second"}]}),
    ).passed is True


def test_json_path_missing_key_returns_none():
    rule = parse_assertion(
        {"type": "json_path", "operator": "exists", "path": "missing"}
    )
    assert evaluate(rule, _resp(json_data={"present": 1})).passed is False


def test_json_path_exists_passes_when_present():
    rule = parse_assertion(
        {"type": "json_path", "operator": "exists", "path": "user.id"}
    )
    assert evaluate(rule, _resp(json_data={"user": {"id": 1}})).passed is True


def test_json_path_not_exists_passes_when_absent():
    rule = parse_assertion(
        {"type": "json_path", "operator": "not_exists", "path": "deleted_at"}
    )
    assert evaluate(rule, _resp(json_data={"id": 1})).passed is True


def test_json_path_list_out_of_range_returns_none():
    rule = parse_assertion(
        {"type": "json_path", "operator": "eq", "path": "items.5", "expected": 0}
    )
    assert evaluate(rule, _resp(json_data={"items": [1, 2]})).passed is False


def test_json_path_negative_index_out_of_range():
    rule = parse_assertion(
        {"type": "json_path", "operator": "eq", "path": "items.-1", "expected": 0}
    )
    assert evaluate(rule, _resp(json_data={"items": [1, 2]})).passed is False


def test_json_path_non_dict_segment_returns_none():
    rule = parse_assertion(
        {"type": "json_path", "operator": "eq", "path": "name.first", "expected": "x"}
    )
    assert evaluate(rule, _resp(json_data={"name": "alice"})).passed is False


def test_json_path_response_not_json_returns_none():
    rule = parse_assertion(
        {"type": "json_path", "operator": "exists", "path": "x"}
    )
    assert evaluate(rule, _resp(text="not json {")).passed is False


def test_json_path_in_with_list():
    rule = parse_assertion(
        {
            "type": "json_path",
            "operator": "in",
            "path": "role",
            "expected": ["admin", "superuser"],
        }
    )
    assert evaluate(rule, _resp(json_data={"role": "admin"})).passed is True


def test_json_path_contains_on_list():
    rule = parse_assertion(
        {
            "type": "json_path",
            "operator": "contains",
            "path": "tags",
            "expected": "urgent",
        }
    )
    assert evaluate(rule, _resp(json_data={"tags": ["urgent", "normal"]})).passed is True


def test_json_path_gt_numeric():
    rule = parse_assertion(
        {"type": "json_path", "operator": "gt", "path": "count", "expected": 10}
    )
    assert evaluate(rule, _resp(json_data={"count": 15})).passed is True


# === 6. header assertions ==================================================


def test_header_eq_exact_match():
    rule = parse_assertion(
        {
            "type": "header",
            "operator": "eq",
            "header_name": "Content-Type",
            "expected": "application/json",
        }
    )
    assert evaluate(
        rule,
        _resp(headers={"Content-Type": "application/json"}),
    ).passed is True


def test_header_lookup_is_case_insensitive():
    """RFC 7230 §3.2 — header names are case-insensitive."""
    rule = parse_assertion(
        {
            "type": "header",
            "operator": "eq",
            "header_name": "content-type",
            "expected": "application/json",
        }
    )
    assert evaluate(
        rule,
        _resp(headers={"Content-Type": "application/json"}),
    ).passed is True


def test_header_eq_fails_on_mismatch():
    rule = parse_assertion(
        {
            "type": "header",
            "operator": "eq",
            "header_name": "Content-Type",
            "expected": "application/xml",
        }
    )
    assert evaluate(
        rule,
        _resp(headers={"Content-Type": "application/json"}),
    ).passed is False


def test_header_contains_substring():
    rule = parse_assertion(
        {
            "type": "header",
            "operator": "contains",
            "header_name": "Content-Type",
            "expected": "json",
        }
    )
    assert evaluate(
        rule,
        _resp(headers={"Content-Type": "application/json"}),
    ).passed is True


def test_header_not_contains_passes_when_absent():
    rule = parse_assertion(
        {
            "type": "header",
            "operator": "not_contains",
            "header_name": "Content-Type",
            "expected": "xml",
        }
    )
    assert evaluate(
        rule,
        _resp(headers={"Content-Type": "application/json"}),
    ).passed is True


def test_header_exists_passes():
    rule = parse_assertion(
        {"type": "header", "operator": "exists", "header_name": "X-Request-ID"}
    )
    assert evaluate(
        rule,
        _resp(headers={"X-Request-ID": "abc-123"}),
    ).passed is True


def test_header_not_exists_passes_when_absent():
    rule = parse_assertion(
        {"type": "header", "operator": "not_exists", "header_name": "X-Debug"}
    )
    assert evaluate(rule, _resp(headers={"Content-Type": "application/json"})).passed is True


def test_header_exists_fails_when_missing():
    rule = parse_assertion(
        {"type": "header", "operator": "exists", "header_name": "X-Trace"}
    )
    assert evaluate(rule, _resp(headers={})).passed is False


# === 7. response_time assertions ===========================================


def test_response_time_lt_passes_within_budget():
    rule = parse_assertion(
        {"type": "response_time", "operator": "lt", "expected": 1.0}
    )
    assert evaluate(rule, _resp(elapsed_seconds=0.5)).passed is True


def test_response_time_lt_fails_when_slow():
    rule = parse_assertion(
        {"type": "response_time", "operator": "lt", "expected": 1.0}
    )
    assert evaluate(rule, _resp(elapsed_seconds=2.5)).passed is False


def test_response_time_ge_passes_for_slow_request():
    rule = parse_assertion(
        {"type": "response_time", "operator": "ge", "expected": 1.0}
    )
    assert evaluate(rule, _resp(elapsed_seconds=1.5)).passed is True


def test_response_time_eq_exact():
    rule = parse_assertion(
        {"type": "response_time", "operator": "eq", "expected": 0.5}
    )
    assert evaluate(rule, _resp(elapsed_seconds=0.5)).passed is True


def test_response_time_string_expected_coerced_to_float():
    """String expected like ``"1.0"`` is coerced after substitution."""
    rule = parse_assertion(
        {"type": "response_time", "operator": "lt", "expected": "1.0"}
    )
    assert evaluate(rule, _resp(elapsed_seconds=0.5)).passed is True


# === 8. body_contains assertions ===========================================


def test_body_contains_substring_match():
    rule = parse_assertion(
        {"type": "body_contains", "operator": "contains", "expected": "success"}
    )
    assert evaluate(rule, _resp(text="operation success")).passed is True


def test_body_contains_fails_on_missing_substring():
    rule = parse_assertion(
        {"type": "body_contains", "operator": "contains", "expected": "success"}
    )
    assert evaluate(rule, _resp(text="operation failure")).passed is False


def test_body_contains_not_contains_passes_when_absent():
    rule = parse_assertion(
        {"type": "body_contains", "operator": "not_contains", "expected": "error"}
    )
    assert evaluate(rule, _resp(text="success")).passed is True


def test_body_contains_case_sensitive_by_default():
    rule = parse_assertion(
        {"type": "body_contains", "operator": "contains", "expected": "SUCCESS"}
    )
    assert evaluate(rule, _resp(text="success")).passed is False


def test_body_contains_case_insensitive_flag():
    rule = parse_assertion(
        {
            "type": "body_contains",
            "operator": "contains",
            "expected": "SUCCESS",
            "case_insensitive": True,
        }
    )
    assert evaluate(rule, _resp(text="success")).passed is True


def test_body_contains_list_expected_all_must_match():
    rule = parse_assertion(
        {
            "type": "body_contains",
            "operator": "contains",
            "expected": ["user", "admin", "active"],
        }
    )
    assert evaluate(rule, _resp(text="user admin active since 2024")).passed is True


def test_body_contains_list_expected_fails_if_any_missing():
    rule = parse_assertion(
        {
            "type": "body_contains",
            "operator": "contains",
            "expected": ["user", "admin", "deleted"],
        }
    )
    assert evaluate(rule, _resp(text="user admin active")).passed is False


def test_body_contains_list_with_case_insensitive():
    rule = parse_assertion(
        {
            "type": "body_contains",
            "operator": "contains",
            "expected": ["USER", "ADMIN"],
            "case_insensitive": True,
        }
    )
    assert evaluate(rule, _resp(text="user admin active")).passed is True


# === 9. evaluate_all =======================================================


def test_evaluate_all_empty_returns_empty_list():
    assert evaluate_all([], _resp()) == []
    assert evaluate_all(None, _resp()) == []


def test_evaluate_all_mixes_types_in_insertion_order():
    rules = [
        {"type": "status_code", "operator": "eq", "expected": 200},
        {"type": "body_contains", "operator": "contains", "expected": "ok"},
    ]
    results = evaluate_all(
        rules,
        _resp(status_code=200, text="<ok>"),
    )
    assert len(results) == 2
    assert results[0].type == "status_code"
    assert results[0].passed is True
    assert results[1].type == "body_contains"
    assert results[1].passed is True


def test_evaluate_all_does_not_short_circuit_on_failure():
    """Even after a failure, every subsequent rule is still evaluated."""
    rules = [
        {"type": "status_code", "operator": "eq", "expected": 200},
        {"type": "body_contains", "operator": "contains", "expected": "ok"},
    ]
    results = evaluate_all(
        rules,
        _resp(status_code=500, text="error"),
    )
    assert len(results) == 2
    assert results[0].passed is False
    assert results[1].passed is False  # body is "error", expected "ok"


def test_evaluate_all_accepts_pre_built_rules():
    """Pre-built :class:`AssertionRule` skips the parse step."""
    rule = AssertionRule(type="status_code", operator="eq", expected=200)
    results = evaluate_all([rule], _resp(status_code=200))
    assert len(results) == 1
    assert results[0].passed is True


def test_evaluate_all_propagates_config_errors_on_parse():
    """If a rule dict is malformed, the exception bubbles up."""
    with pytest.raises(AssertionConfigError):
        evaluate_all(
            [{"type": "json_path", "operator": "eq", "expected": 1}],  # missing path
            _resp(),
        )


# === 10. F008 integration — variable substitution =========================


def test_expected_uses_f008_substitution_simple():
    """``${var}`` is resolved via F008 before comparison."""
    rule = parse_assertion(
        {"type": "status_code", "operator": "eq", "expected": "${code}"}
    )
    result = evaluate(rule, _resp(status_code=200), variables={"code": 200})
    assert result.passed is True


def test_expected_uses_f008_substitution_with_builtin():
    """``${timestamp}`` is type-coerced to int for ``status_code`` and
    compared against the actual status code (set to the same value)."""
    import time

    timestamp = int(time.time())
    rule = parse_assertion(
        {
            "type": "status_code",
            "operator": "eq",
            "expected": "${timestamp}",
        }
    )
    result = evaluate(rule, _resp(status_code=timestamp))
    assert result.expected == timestamp
    assert result.passed is True


def test_expected_substitution_with_response_time():
    rule = parse_assertion(
        {"type": "response_time", "operator": "lt", "expected": "${budget}"}
    )
    result = evaluate(rule, _resp(elapsed_seconds=0.5), variables={"budget": "1.0"})
    assert result.passed is True
    assert result.expected == 1.0


def test_expected_substitution_in_body_contains():
    rule = parse_assertion(
        {"type": "body_contains", "operator": "contains", "expected": "${marker}"}
    )
    result = evaluate(
        rule,
        _resp(text="hello world"),
        variables={"marker": "world"},
    )
    assert result.passed is True


def test_expected_missing_variable_keeps_placeholder_string():
    """F008 keeps the placeholder; the engine then string-compares against it."""
    rule = parse_assertion(
        {"type": "body_contains", "operator": "contains", "expected": "${nope}"}
    )
    # F008's substitute leaves "${nope}" in place and logs a warning;
    # the engine then sees the literal placeholder string and fails.
    result = evaluate(rule, _resp(text="${nope}"))
    assert result.passed is True  # body literally contains "${nope}"


# === 11. Error-code mapping ================================================


def test_unsupported_type_maps_to_31004_conceptually():
    """``UnsupportedAssertionTypeError`` is distinct from config errors."""
    with pytest.raises(UnsupportedAssertionTypeError) as exc_info:
        AssertionRule(type="regex_match", operator="eq", expected=".*")
    # The message includes the offending type so callers can log it.
    assert "regex_match" in str(exc_info.value)


def test_unsupported_operator_maps_to_31005_conceptually():
    """``UnsupportedAssertionOperatorError`` is distinct from config errors."""
    with pytest.raises(UnsupportedAssertionOperatorError):
        AssertionRule(
            type="response_time",
            operator="contains",
            expected="x",
        )


def test_config_error_maps_to_31003_conceptually():
    """``AssertionConfigError`` covers missing/wrong fields."""
    with pytest.raises(AssertionConfigError):
        AssertionRule(type="header", operator="exists")  # missing header_name


def test_all_engine_errors_inherit_from_base():
    """Every F009 exception is catchable as ``AssertionEngineError``."""
    excs = [
        AssertionConfigError("x"),
        UnsupportedAssertionTypeError("x"),
        UnsupportedAssertionOperatorError("x"),
    ]
    for exc in excs:
        assert isinstance(exc, AssertionEngineError)


# === 12. Result data class =================================================


def test_assertion_result_dataclass_fields():
    result = AssertionResult(
        type="status_code",
        operator="eq",
        passed=True,
        actual=200,
        expected=200,
        message="ok",
    )
    assert result.type == "status_code"
    assert result.passed is True
    assert result.message == "ok"
    assert result.path is None
    assert result.header_name is None


def test_assertion_result_truthy_when_passed():
    result = AssertionResult(
        type="x", operator="y", passed=True, actual=1, expected=1, message=""
    )
    assert bool(result) is True


def test_assertion_result_falsy_when_failed():
    result = AssertionResult(
        type="x", operator="y", passed=False, actual=1, expected=2, message=""
    )
    assert bool(result) is False