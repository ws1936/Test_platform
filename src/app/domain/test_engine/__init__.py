"""API test engine domain primitives.

This package holds the *stateless*, *engine-internal* helpers that the
F010 executor will compose when running a test case:

* :mod:`app.domain.test_engine.assertions` — F009 rule-based assertion
  evaluator (``status_code`` / ``json_path`` / ``header`` /
  ``response_time`` / ``body_contains``).
* :mod:`app.domain.test_engine.exceptions` — engine-specific
  exceptions (configuration errors, unsupported types / operators).

There is intentionally **no** Router, Service, or Repository here —
the engine is a pure-function library that takes already-loaded data
and returns results, mirroring F008's ``variable_substitutor``.
"""

from app.domain.test_engine.assertions import (
    ALLOWED_OPERATORS,
    ALLOWED_TYPES,
    AssertionOperator,
    AssertionResult,
    AssertionRule,
    AssertionType,
    evaluate,
    evaluate_all,
    parse_assertion,
)
from app.domain.test_engine.exceptions import (
    AssertionConfigError,
    AssertionEngineError,
    UnsupportedAssertionOperatorError,
    UnsupportedAssertionTypeError,
)

__all__ = [
    # Constants
    "ALLOWED_OPERATORS",
    "ALLOWED_TYPES",
    # Type aliases (for documentation / type-checker use)
    "AssertionType",
    "AssertionOperator",
    # Core data classes
    "AssertionRule",
    "AssertionResult",
    # Public API
    "parse_assertion",
    "evaluate",
    "evaluate_all",
    # Exceptions
    "AssertionEngineError",
    "AssertionConfigError",
    "UnsupportedAssertionTypeError",
    "UnsupportedAssertionOperatorError",
]