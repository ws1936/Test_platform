"""F009 Assertion Engine — rule-based assertion evaluator.

Public surface
--------------
* :func:`parse_assertion` — validate and shape a raw dict into an
  :class:`AssertionRule`.
* :func:`evaluate` — evaluate one rule against a response.
* :func:`evaluate_all` — evaluate a list of rules and return all
  results (no short-circuit, so the report can show every failure).

Design notes
------------
* **Pure functions only** — no I/O, no logging side effects, no
  global state apart from F008's builtin registry.
* **No Pydantic for the rule model** — a ``@dataclass`` is used so
  custom exceptions (``UnsupportedAssertionTypeError`` etc.) propagate
  directly instead of being wrapped in ``pydantic.ValidationError``.
* **``expected`` is variable-substituted** via F008's ``substitute``
  before comparison, per PRD §5.5 ("变量可用于 path、headers、
  query、body **和断言 expected 值**").
* **Type-aware expected coercion**: for ``status_code`` (→ ``int``)
  and ``response_time`` (→ ``float``), the resolved string is
  parsed; non-numeric values are passed through so the comparator
  can produce a meaningful failure message.
* **Path missing ⇒ ``None``** so ``exists`` / ``not_exists`` work
  naturally without a special branch.
* **Header lookup is case-insensitive** to match RFC 7230 §3.2.
* **body_contains supports ``case_insensitive``** flag.

Out of scope (deferred)
-----------------------
* User-defined scripted assertions (PRD §5.6 explicitly forbids).
* jsonpath-ng-style expressions (``$['users'][0]['id']``); we ship a
  deliberately small grammar per the F009 brief recommendation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from app.domain.test_engine.exceptions import (
    AssertionConfigError,
    UnsupportedAssertionOperatorError,
    UnsupportedAssertionTypeError,
)
from app.services.variable_substitutor import substitute


# ---------------------------------------------------------------------------
# Type / operator taxonomy
# ---------------------------------------------------------------------------

# These string-literal sets are the canonical allowlist. Re-declared as
# ``frozenset`` for O(1) membership tests inside ``__post_init__``.
ALLOWED_TYPES: frozenset[str] = frozenset(
    {"status_code", "json_path", "header", "response_time", "body_contains"}
)

ALLOWED_OPERATORS: frozenset[str] = frozenset(
    {
        "eq", "ne",
        "gt", "lt", "ge", "le",
        "contains", "not_contains",
        "in", "not_in",
        "exists", "not_exists",
    }
)

# Per-type operator allowlist. These combinations are deliberate:
#
# * ``status_code`` and ``response_time`` are scalar numeric — orderable
#   operators apply, ``in/not_in`` only on ``status_code`` (time range
#   sets are unusual).
# * ``json_path`` returns arbitrary JSON — every operator applies,
#   including ``exists/not_exists`` for path presence.
# * ``header`` returns strings — only string operators + existence.
# * ``body_contains`` is a single-shot substring check.
_TYPE_TO_OPERATORS: dict[str, frozenset[str]] = {
    "status_code": frozenset({"eq", "ne", "gt", "lt", "ge", "le", "in", "not_in"}),
    "json_path": frozenset(
        {
            "eq", "ne", "gt", "lt", "ge", "le",
            "contains", "not_contains",
            "in", "not_in",
            "exists", "not_exists",
        }
    ),
    "header": frozenset(
        {"eq", "ne", "contains", "not_contains", "exists", "not_exists"}
    ),
    "response_time": frozenset({"eq", "ne", "gt", "lt", "ge", "le"}),
    "body_contains": frozenset({"contains", "not_contains"}),
}


# Type aliases — documentation / static type-checker use only.
AssertionType = str  # one of ALLOWED_TYPES
AssertionOperator = str  # one of ALLOWED_OPERATORS


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AssertionRule:
    """One validated assertion rule.

    Always construct via :func:`parse_assertion` so that all per-type
    invariants are checked. Direct construction is allowed but skips
    validation, which is fine for tests that already validated the
    shape.
    """

    type: str
    operator: str
    expected: Any = None
    path: Optional[str] = None
    header_name: Optional[str] = None
    case_insensitive: bool = False

    def __post_init__(self) -> None:
        # --- 1. type is in the supported set --------------------------
        if self.type not in _TYPE_TO_OPERATORS:
            raise UnsupportedAssertionTypeError(
                f"unsupported assertion type: {self.type!r}; "
                f"allowed: {sorted(ALLOWED_TYPES)}"
            )

        # --- 2. operator is allowed for the given type ---------------
        allowed_ops = _TYPE_TO_OPERATORS[self.type]
        if self.operator not in allowed_ops:
            raise UnsupportedAssertionOperatorError(
                f"operator {self.operator!r} is not supported for type "
                f"{self.type!r}; allowed: {sorted(allowed_ops)}"
            )

        # --- 3. expected presence / absence rules --------------------
        needs_expected = self.operator not in {"exists", "not_exists"}
        if needs_expected and self.expected is None:
            raise AssertionConfigError(
                f"operator {self.operator!r} requires an 'expected' value"
            )

        # --- 4. type-specific required / forbidden fields -------------
        if self.type == "json_path":
            if not self.path:
                raise AssertionConfigError(
                    "'path' is required for json_path assertions"
                )
        elif self.path is not None:
            raise AssertionConfigError(
                f"'path' is only valid for json_path assertions, "
                f"not {self.type!r}"
            )

        if self.type == "header":
            if not self.header_name:
                raise AssertionConfigError(
                    "'header_name' is required for header assertions"
                )
        elif self.header_name is not None:
            raise AssertionConfigError(
                f"'header_name' is only valid for header assertions, "
                f"not {self.type!r}"
            )

        if self.case_insensitive and self.type != "body_contains":
            raise AssertionConfigError(
                "'case_insensitive' is only valid for body_contains "
                "assertions"
            )


@dataclass
class AssertionResult:
    """Outcome of evaluating one :class:`AssertionRule`."""

    type: str
    operator: str
    passed: bool
    actual: Any
    expected: Any
    message: str
    path: Optional[str] = None
    header_name: Optional[str] = None

    def __bool__(self) -> bool:  # pragma: no cover - convenience only
        return self.passed


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_assertion(data: Mapping[str, Any]) -> AssertionRule:
    """Parse a raw assertion dict into a validated :class:`AssertionRule`.

    Required keys: ``type``, ``operator``.
    Optional keys: ``expected``, ``path``, ``header_name``,
    ``case_insensitive``.

    Raises:
        UnsupportedAssertionTypeError: ``type`` is not one of the 5
            supported types.
        UnsupportedAssertionOperatorError: ``operator`` is not allowed
            for the given ``type``.
        AssertionConfigError: a required field is missing, or a
            type-specific constraint is violated.
        KeyError: ``type`` or ``operator`` is missing from ``data``.
    """
    return AssertionRule(
        type=data["type"],
        operator=data["operator"],
        expected=data.get("expected"),
        path=data.get("path"),
        header_name=data.get("header_name"),
        case_insensitive=bool(data.get("case_insensitive", False)),
    )


# ---------------------------------------------------------------------------
# Public evaluation API
# ---------------------------------------------------------------------------


def evaluate(
    rule: AssertionRule,
    response: Any,
    variables: Mapping[str, Any] | None = None,
) -> AssertionResult:
    """Evaluate one :class:`AssertionRule` against ``response``.

    ``variables`` is forwarded to F008's :func:`substitute` so that
    ``${...}`` placeholders inside ``expected`` are resolved before
    the comparison is made.

    The returned :class:`AssertionResult` is *always* populated
    (never raises) — every comparison either passes or fails
    gracefully. Type errors in the rule surface as a failing
    ``AssertionResult`` with a descriptive message rather than an
    exception, so the caller can render all failures in one report.
    """
    actual = _extract_actual(response, rule)
    resolved_expected = _resolve_expected(rule.expected, variables, rule.type)
    passed, message = _compare(actual, rule.operator, resolved_expected, rule)

    return AssertionResult(
        type=rule.type,
        operator=rule.operator,
        passed=passed,
        actual=actual,
        expected=resolved_expected,
        message=message,
        path=rule.path,
        header_name=rule.header_name,
    )


def evaluate_all(
    rules: Sequence[Mapping[str, Any] | AssertionRule] | None,
    response: Any,
    variables: Mapping[str, Any] | None = None,
) -> list[AssertionResult]:
    """Evaluate every rule in order and return one result per rule.

    *Does not short-circuit on failure* — PRD §5.8 requires the
    report to surface all assertion results in one go, so a later
    rule's failure is not hidden behind an earlier failure.

    Each ``rule`` may be either a pre-built :class:`AssertionRule`
    or a raw mapping that will be fed through :func:`parse_assertion`.
    """
    if not rules:
        return []
    results: list[AssertionResult] = []
    for entry in rules:
        if isinstance(entry, AssertionRule):
            rule = entry
        else:
            rule = parse_assertion(entry)
        results.append(evaluate(rule, response, variables))
    return results


# ---------------------------------------------------------------------------
# Value extraction
# ---------------------------------------------------------------------------


def _extract_actual(response: Any, rule: AssertionRule) -> Any:
    """Pull the actual value from ``response`` based on ``rule.type``.

    Returns ``None`` for missing paths / headers so the comparison
    operators ``exists`` / ``not_exists`` work naturally.
    """
    if rule.type == "status_code":
        return int(getattr(response, "status_code", 0))

    if rule.type == "json_path":
        try:
            body = response.json()
        except (ValueError, TypeError):
            return None
        return _resolve_json_path(body, rule.path or "")

    if rule.type == "header":
        if not rule.header_name:
            return None
        # HTTP header names are case-insensitive (RFC 7230 §3.2).
        target = rule.header_name.lower()
        for key, value in response.headers.items():
            if key.lower() == target:
                return value
        return None

    if rule.type == "response_time":
        elapsed = getattr(response, "elapsed", None)
        if elapsed is None:
            return None
        return elapsed.total_seconds()

    if rule.type == "body_contains":
        return getattr(response, "text", "") or ""

    # Should be unreachable — ``parse_assertion`` validates ``type``.
    raise UnsupportedAssertionTypeError(  # pragma: no cover
        f"unsupported assertion type: {rule.type!r}"
    )


# Matches ``[0]`` / ``[12]`` (positive integer index in square brackets).
_JSON_PATH_BRACKET_RE = re.compile(r"\[(\d+)\]")


def _resolve_json_path(data: Any, path: str) -> Any:
    """Navigate ``data`` by ``path``.

    Grammar (deliberately small per F009 brief):

    * ``user.id``        — dict key navigation via ``.``
    * ``items.0.name``   — list index via numeric token
    * ``items[0].name``  — bracket notation (rewritten to dotted)

    Returns ``None`` if any intermediate segment is missing or the
    requested index is out of range.
    """
    if not path:
        return None
    normalized = _JSON_PATH_BRACKET_RE.sub(r".\1", path)
    parts = [p for p in normalized.split(".") if p != ""]
    current: Any = data
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list):
            try:
                idx = int(part)
            except ValueError:
                return None
            if idx < 0 or idx >= len(current):
                return None
            current = current[idx]
        else:
            return None
    return current


# ---------------------------------------------------------------------------
# ``expected`` resolution
# ---------------------------------------------------------------------------


def _resolve_expected(
    expected: Any,
    variables: Mapping[str, Any] | None,
    type_: str,
) -> Any:
    """Resolve ``expected`` against F008 ``substitute``, then coerce.

    Non-string ``expected`` values (lists / dicts / numbers supplied
    by the caller) pass through unchanged. Strings are first
    variable-substituted, then type-coerced for ``status_code`` /
    ``response_time`` so the comparator does not have to know about
    the JSON-typed ``expected`` versus the ``"200"``-typed one.
    """
    if expected is None:
        return None
    if not isinstance(expected, str):
        return expected
    substituted = substitute(expected, variables)
    if type_ == "status_code":
        try:
            return int(substituted)
        except (TypeError, ValueError):
            return substituted
    if type_ == "response_time":
        try:
            return float(substituted)
        except (TypeError, ValueError):
            return substituted
    return substituted


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def _compare(
    actual: Any,
    operator: str,
    expected: Any,
    rule: AssertionRule,
) -> tuple[bool, str]:
    """Compare ``actual`` vs ``expected`` using ``operator``.

    Returns ``(passed, message)``. Failures include a descriptive
    message; passes include a short confirmation.
    """
    # --- 1. existence checks (don't need ``expected``) -----------------
    if operator == "exists":
        return (actual is not None, _fmt("exists", actual, expected))
    if operator == "not_exists":
        return (actual is None, _fmt("not_exists", actual, expected))

    # --- 2. type-specific case folding --------------------------------
    ci = rule.case_insensitive and rule.type == "body_contains"
    cmp_actual = _apply_case_insensitive(actual, ci)
    cmp_expected = _apply_case_insensitive(expected, ci)

    # --- 3. equality / inequality -------------------------------------
    if operator == "eq":
        return (cmp_actual == cmp_expected, _fmt("eq", actual, expected))
    if operator == "ne":
        return (cmp_actual != cmp_expected, _fmt("ne", actual, expected))

    # --- 4. orderable comparisons -------------------------------------
    if operator in {"gt", "lt", "ge", "le"}:
        try:
            if operator == "gt":
                return (cmp_actual > cmp_expected, _fmt("gt", actual, expected))
            if operator == "lt":
                return (cmp_actual < cmp_expected, _fmt("lt", actual, expected))
            if operator == "ge":
                return (cmp_actual >= cmp_expected, _fmt("ge", actual, expected))
            return (cmp_actual <= cmp_expected, _fmt("le", actual, expected))
        except TypeError as exc:
            return (
                False,
                f"cannot apply {operator!r} to "
                f"{type(actual).__name__} and {type(expected).__name__}: {exc}",
            )

    # --- 5. containment ----------------------------------------------
    if operator == "contains":
        passed, msg = _do_contains(
            cmp_actual,
            cmp_expected,
            original_actual=actual,
            original_expected=expected,
        )
        return (passed, msg)
    if operator == "not_contains":
        # ``not_contains`` is the inverse of ``contains``: the rule
        # passes when ``expected`` is *not* present in ``actual``.
        passed, msg = _do_contains(
            cmp_actual,
            cmp_expected,
            original_actual=actual,
            original_expected=expected,
        )
        return (not passed, msg)

    # --- 6. set membership --------------------------------------------
    if operator in {"in", "not_in"}:
        if not isinstance(expected, (list, tuple, set, frozenset)):
            return (
                False,
                f"'{operator}' operator requires expected to be a "
                f"collection, got {type(expected).__name__}",
            )
        if operator == "in":
            return (cmp_actual in expected, _fmt("in", actual, expected))
        return (cmp_actual not in expected, _fmt("not_in", actual, expected))

    # Should be unreachable — ``parse_assertion`` validates ``operator``.
    raise UnsupportedAssertionOperatorError(  # pragma: no cover
        f"unsupported operator: {operator!r}"
    )


def _do_contains(
    actual: Any,
    expected: Any,
    *,
    original_actual: Any,
    original_expected: Any,
) -> tuple[bool, str]:
    """Handle the ``contains`` operator against three shapes:

    * ``expected`` is a ``list`` / ``tuple`` — every element must be
      present in ``actual``.
    * ``expected`` is a scalar ``str`` and ``actual`` is a ``str`` —
      substring check.
    * Otherwise — element membership (``expected in actual``).

    The ``not_contains`` operator is handled by the caller inverting
    the returned ``passed`` value, so this function never has to know
    whether the rule is negated.

    Any ``TypeError`` raised by ``in`` falls through to ``False``.
    """
    label = "contains"
    if actual is None:
        return (False, _fmt(label, original_actual, original_expected))

    if isinstance(expected, (list, tuple)):
        try:
            for item in expected:
                if item not in actual:
                    return (False, _fmt(label, original_actual, original_expected))
            return (True, _fmt_pass(label, original_actual, original_expected))
        except TypeError:
            return (False, _fmt(label, original_actual, original_expected))

    if isinstance(actual, str) and isinstance(expected, str):
        return (
            expected in actual,
            _fmt(label, original_actual, original_expected),
        )

    try:
        return (
            expected in actual,
            _fmt(label, original_actual, original_expected),
        )
    except TypeError:
        return (False, _fmt(label, original_actual, original_expected))


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _fmt(op: str, actual: Any, expected: Any) -> str:
    """Format a typically-failing assertion message."""
    return f"{op}: actual={actual!r} expected={expected!r}"


def _fmt_pass(op: str, actual: Any, expected: Any) -> str:
    """Format a passing assertion message."""
    return f"{op}: passed (actual={actual!r} expected={expected!r})"


def _apply_case_insensitive(value: Any, enabled: bool) -> Any:
    """Recursively lower-case strings when ``enabled`` is True.

    Used for ``body_contains`` to support ``case_insensitive`` without
    duplicating the logic in every comparison branch.
    """
    if not enabled:
        return value
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, list):
        return [_apply_case_insensitive(v, enabled) for v in value]
    if isinstance(value, tuple):
        return tuple(_apply_case_insensitive(v, enabled) for v in value)
    return value