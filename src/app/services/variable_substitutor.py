"""Variable substitution for API test request templates (F008).

Scope
-----
F008 ships a *stateless*, *string-level* placeholder replacer:

* Placeholder syntax is ``${name}`` where ``name`` is a standard
  Python-style identifier (``[A-Za-z_][A-Za-z0-9_]*``). This is the
  syntax requested by the F008 task brief; PRD §5.5 mentions a
  similar ``{{name}}`` syntax for the long-term plan, but the MVP
  ships with the simpler ``${name}`` form.
* Missing variables are left intact in the output and a warning is
  logged — execution paths must never abort on a missing variable
  before F009 / F010 can attach a 400-level response.
* A small set of built-in placeholders is generated lazily so tests
  can monkeypatch the underlying clock deterministically.
* The function is pure (apart from logging and the clock) so it can
  be unit-tested without any database, HTTP, or service fixture.

Out of scope
------------
* Nested placeholders (``${outer_${inner}}``) are intentionally not
  supported — the regex stops at the first ``}`` so callers cannot
  accidentally trigger exponential-time blowups.
* Escape sequences (``\\${x}``) are not supported — same rationale.
* Type coercion beyond ``str(value)`` is the caller's responsibility.
  Booleans render as ``"True"`` / ``"False"``; numbers render with
  their ``str()`` form.

Caller responsibilities
----------------------
The function does not merge multiple mappings itself; the caller
passes a *single* merged ``dict``. This keeps the function trivially
testable and lets the caller decide the priority order (the typical
recipe is ``{**defaults, **overrides}``). Built-in placeholders are
the lowest priority: a user-supplied ``timestamp`` always wins.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Callable, Mapping, MutableMapping


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Placeholder syntax
# ---------------------------------------------------------------------------

# A placeholder is ``${<identifier>}`` where ``<identifier>`` matches
# the standard Python identifier production:
#   identifier ::= [_A-Za-z][_A-Za-z0-9]*
# We deliberately do *not* allow nested braces — the regex is greedy
# only up to the first closing ``}``.
_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


# ---------------------------------------------------------------------------
# Built-in placeholders
# ---------------------------------------------------------------------------


def _builtin_timestamp() -> str:
    """Return the current Unix timestamp (seconds) as a decimal string.

    Wrapped in a dedicated helper so tests can ``monkeypatch`` it
    deterministically — patching ``time.time`` directly would couple
    unrelated tests to the global clock implementation.
    """
    return str(int(time.time()))


# Map of built-in placeholder name → factory. Factories (not values)
# are stored so each substitution evaluates the clock freshly. The
# dict is intentionally module-private — callers extend it via the
# ``variables`` argument.
_BUILTINS: MutableMapping[str, Callable[[], str]] = {
    "timestamp": _builtin_timestamp,
}


def register_builtin(name: str, factory: Callable[[], str]) -> None:
    """Register a new built-in placeholder.

    Provided for future expansion (e.g. ``${uuid}`` / ``${random_int}``
    in F010). Tests may use this to inject deterministic built-ins
    without monkeypatching the module clock.
    """
    if not _PLACEHOLDER_RE.match("${" + name + "}"):
        raise ValueError(
            f"builtin name {name!r} is not a valid placeholder identifier"
        )
    _BUILTINS[name] = factory


def _builtin_value(name: str) -> str | None:
    """Resolve a built-in name to its current value, or ``None``."""
    factory = _BUILTINS.get(name)
    if factory is None:
        return None
    return factory()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def substitute(
    template: str,
    variables: Mapping[str, object] | None = None,
) -> str:
    """Return ``template`` with every ``${name}`` placeholder replaced.

    Args:
        template: Source string. May contain zero or more placeholders.
        variables: Mapping of name → value. Values are coerced to
            ``str`` via ``str(value)``. Passing ``None`` is equivalent
            to passing an empty mapping.

    Returns:
        A new string with every known placeholder replaced. Unknown
        placeholders are kept verbatim and a warning is logged so the
        caller can decide whether to abort.

    Notes:
        * The function does **not** mutate ``variables``.
        * User-supplied values always override built-ins of the same
          name (priority: ``user > builtin``).
        * The caller is responsible for merging multiple dictionaries
          before calling; the typical recipe is
          ``{**defaults, **overrides}`` to let ``overrides`` win.
    """
    if template is None:
        raise TypeError("template must be a string, not None")

    if variables is None:
        user_vars: Mapping[str, object] = {}
    else:
        user_vars = variables

    def _replace(match: "re.Match[str]") -> str:
        name = match.group(1)
        if name in user_vars:
            return str(user_vars[name])
        builtin = _builtin_value(name)
        if builtin is not None:
            return builtin
        # Missing variable — keep the placeholder so callers can see
        # what went wrong and emit a single warning per occurrence.
        logger.warning(
            "VariableSubstitutor: variable %r not found, "
            "keeping original placeholder %s",
            name,
            match.group(0),
        )
        return match.group(0)

    return _PLACEHOLDER_RE.sub(_replace, template)