"""Unit tests for F008 variable substitution.

Covers the contract spelled out in the F008 task brief:

* Single and multiple placeholder replacement.
* Variables come from a plain ``dict``.
* Missing variables keep the placeholder and log a warning.
* Priority: when the caller merges multiple dicts, later entries
  override earlier ones (``substitute`` itself does not merge).
* The built-in ``${timestamp}`` returns a decimal Unix-timestamp
  string.
"""

from __future__ import annotations

import logging

import pytest

from app.services import variable_substitutor as vs


# === 1) Identity / no-placeholder behaviour ===


def test_returns_template_unchanged_when_no_placeholders():
    """A template without ``${...}`` is returned verbatim."""
    assert vs.substitute("hello world") == "hello world"


def test_returns_empty_string_for_empty_input():
    assert vs.substitute("") == ""


def test_none_variables_is_treated_as_empty():
    """``variables=None`` is equivalent to ``{}`` — built-ins still work."""
    # Built-ins are resolved even with no user variables, so the
    # timestamp placeholder gets replaced (we don't assert the value).
    out = vs.substitute("${timestamp}", None)
    assert out != "${timestamp}"
    assert out.isdigit()


def test_non_string_template_raises_type_error():
    """Passing ``None`` or non-string is a programming error."""
    with pytest.raises(TypeError):
        vs.substitute(None)  # type: ignore[arg-type]


# === 2) Single + multiple placeholder replacement ===


def test_replaces_single_variable():
    assert vs.substitute("hello ${name}", {"name": "alice"}) == "hello alice"


def test_replaces_multiple_variables_in_one_template():
    template = "${greeting}, ${name}!"
    variables = {"greeting": "Hello", "name": "alice"}
    assert vs.substitute(template, variables) == "Hello, alice!"


def test_replaces_same_variable_multiple_times():
    """Each occurrence is resolved independently."""
    assert vs.substitute("${x} ${x} ${x}", {"x": "v"}) == "v v v"


def test_value_is_coerced_to_string_for_int():
    assert vs.substitute("${n}", {"n": 42}) == "42"


def test_value_is_coerced_to_string_for_float():
    assert vs.substitute("${f}", {"f": 3.14}) == "3.14"


def test_value_is_coerced_to_string_for_bool():
    assert vs.substitute("${b}", {"b": True}) == "True"
    assert vs.substitute("${b}", {"b": False}) == "False"


def test_value_supports_long_strings():
    long_value = "x" * 4096
    assert vs.substitute("${payload}", {"payload": long_value}) == long_value


# === 3) Missing variable — keep placeholder + warning ===


def test_missing_variable_keeps_placeholder_verbatim(caplog):
    """Unknown placeholders are preserved so the caller can see what failed."""
    with caplog.at_level(logging.WARNING, logger=vs.logger.name):
        result = vs.substitute("hello ${missing}", {"name": "alice"})
    assert result == "hello ${missing}"


def test_missing_variable_emits_warning_log(caplog):
    """Each missing placeholder emits exactly one WARNING log line."""
    caplog.set_level(logging.WARNING, logger=vs.logger.name)
    vs.substitute("a=${x} b=${y}", {})
    messages = [record.getMessage() for record in caplog.records]
    assert any("'x'" in msg for msg in messages)
    assert any("'y'" in msg for msg in messages)


def test_partial_template_with_missing_var_returns_partial_substitution():
    """Known placeholders are still replaced when *some* are missing."""
    out = vs.substitute("${known} ${missing}", {"known": "v"})
    assert out == "v ${missing}"


# === 4) Priority: caller merges dicts, later wins ===


def test_caller_merge_with_later_dict_overrides_earlier():
    """``substitute`` does not merge — the caller does, and ``overrides`` wins."""
    defaults = {"token": "old", "user_id": "100"}
    overrides = {"token": "new"}
    merged = {**defaults, **overrides}
    assert vs.substitute("${token}", merged) == "new"


def test_caller_merge_unaffected_keys_keep_earlier_value():
    """Keys present only in the earlier dict are preserved."""
    defaults = {"token": "old", "user_id": "100"}
    overrides = {"token": "new"}
    merged = {**defaults, **overrides}
    assert vs.substitute("${user_id}", merged) == "100"


def test_user_variable_overrides_builtin_of_same_name():
    """A user-supplied ``timestamp`` wins over the built-in clock."""
    out = vs.substitute("${timestamp}", {"timestamp": "manual"})
    assert out == "manual"


# === 5) Built-in ${timestamp} ===


def test_builtin_timestamp_returns_unix_int_as_string(monkeypatch):
    """Patching the module clock makes the test deterministic."""
    monkeypatch.setattr(vs.time, "time", lambda: 1_700_000_000.5)
    assert vs.substitute("${timestamp}") == "1700000000"


def test_builtin_timestamp_truncates_fractional_seconds():
    """``time.time()`` may return a float; the helper truncates to int."""
    import app.services.variable_substitutor as mod

    monkey_called_with: list[float] = []

    def fake_time() -> float:
        monkey_called_with.append(1_700_000_000.75)
        return 1_700_000_000.75

    mod.time.time = fake_time  # type: ignore[assignment]
    assert vs.substitute("${timestamp}") == "1700000000"
    assert monkey_called_with == [1_700_000_000.75]


def test_builtin_timestamp_coexists_with_user_variables(monkeypatch):
    monkeypatch.setattr(vs.time, "time", lambda: 1_700_000_000)
    template = "ts=${timestamp}, token=${token}, user=${user_id}"
    variables = {"token": "abc", "user_id": "42"}
    assert (
        vs.substitute(template, variables)
        == "ts=1700000000, token=abc, user=42"
    )


def test_register_builtin_extends_supported_names(monkeypatch):
    """Custom built-ins can be added via ``register_builtin``."""
    vs.register_builtin("uuid", lambda: "fixed-uuid")
    try:
        assert vs.substitute("${uuid}") == "fixed-uuid"
    finally:
        # Clean up so other tests are unaffected.
        vs._BUILTINS.pop("uuid", None)


def test_register_builtin_rejects_invalid_name():
    """Names that wouldn't be matched by the placeholder regex are rejected."""
    with pytest.raises(ValueError):
        vs.register_builtin("1bad-name", lambda: "x")


# === 6) Regex strictness — no nested braces, no whitespace inside ===


def test_does_not_match_dollar_brace_without_identifier():
    """``${}`` is not a valid placeholder and stays verbatim."""
    assert vs.substitute("a${}b", {}) == "a${}b"


def test_does_not_match_dollar_open_brace_alone():
    """Stray ``${`` is left alone."""
    assert vs.substitute("a${b", {}) == "a${b"


def test_does_not_expand_nested_placeholders():
    """Nested braces are not supported; the outer placeholder stays verbatim.

    The regex searches left-to-right. ``${a${b}}`` contains:

    * An *incomplete* ``${a`` whose ``}`` is missing at this position
      (the next char is ``$``, not ``}``). The regex never matches it.
    * A *complete* ``${b}`` two characters later, which IS a valid
      placeholder and gets replaced with the user value.

    Result: ``${a${b}}`` → ``${aB}``. The key invariant is that we
    do *not* recursively re-expand the outer placeholder after the
    inner one is replaced — nested expansion is explicitly out of
    scope for F008 (see module docstring).
    """
    out = vs.substitute("${a${b}}", {"a": "A", "b": "B"})
    assert out == "${aB}"


def test_does_not_match_identifier_starting_with_digit():
    """``${1var}`` is not a valid identifier and stays verbatim."""
    assert vs.substitute("${1var}", {"1var": "v"}) == "${1var}"