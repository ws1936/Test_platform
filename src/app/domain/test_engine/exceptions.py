"""Custom exceptions for the API test engine.

Three exception classes mirror the three error-code buckets reserved
for F009 in ``docs/03-api/ERROR_CODE.md`` §5:

* :class:`AssertionConfigError`  → **31003** — malformed rule
  (missing field, wrong shape, type-specific constraint violated).
* :class:`UnsupportedAssertionTypeError`     → **31004** — ``type``
  is not one of the 5 supported assertion types.
* :class:`UnsupportedAssertionOperatorError` → **31005** — ``operator``
  is not supported for the given ``type``.

These inherit from :class:`Exception` (not ``ValueError``) so they
propagate cleanly through Pydantic validators and asyncio without
being wrapped in ``ValidationError`` / ``ValueError`` machinery. The
HTTP / F010 layer is responsible for translating these to
business-error responses with the codes above.

Why not subclass ``AppException``?
----------------------------------
The engine is a pure-function library used inside F010 (executor);
HTTP-layer concerns (status codes, response envelopes) live at the
edge. Coupling ``AppException`` here would force every test of the
engine to import the HTTP stack.
"""

from __future__ import annotations


class AssertionEngineError(Exception):
    """Base class for all assertion-engine errors.

    Catching this base is the recommended way for callers (F010
    executor, preview endpoints) to convert engine failures into
    API-level responses without depending on a specific subclass.
    """


class AssertionConfigError(AssertionEngineError):
    """The assertion rule is malformed.

    Raised when:

    * A required field is missing for a given ``type``/``operator``
      combination (e.g. ``path`` missing on a ``json_path`` rule).
    * A field is supplied that does not apply to the chosen type
      (e.g. ``header_name`` on a ``status_code`` rule).
    * The ``expected`` value is missing for an operator that needs it.

    Maps to **31003**.
    """


class UnsupportedAssertionTypeError(AssertionEngineError):
    """The ``type`` field is not one of the 5 supported types.

    Maps to **31004**.
    """


class UnsupportedAssertionOperatorError(AssertionEngineError):
    """The ``operator`` is not supported for the given ``type``.

    Maps to **31005**. The combination rules are documented in
    :data:`app.domain.test_engine.assertions._TYPE_TO_OPERATORS`.
    """