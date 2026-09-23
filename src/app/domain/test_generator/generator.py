"""F023 TestGenerator — pure function converting TestIntent → TestCaseCreateRequest.

Design contract (see ``docs/01-product/F023_SPEC.md`` §3.1 + ADR-009):

* Stateless: no DB, no HTTP, no logger side-effects. The instance only
  exists for the call-site ergonomic; ``intent_to_request`` could equally
  well be a ``@staticmethod``.
* Per-intent: each ``TestIntent`` → one ``TestCaseCreateRequest``.
* Auto-assertions: only happy_path intents gain automatic json_path /
  header assertions (per SPEC §3.2 / ADR-009 decision 5 — silent skip when
  the response schema is absent).
* Backwards-compat: F012's existing ``design=simple`` byte-equivalent
  path does **not** invoke this class — see service.py. So this generator
  is the single source of truth only for ``design=schema``.
"""

from __future__ import annotations

import copy
from typing import Any, Optional

from app.domain.openapi_importer.parser import Operation
from app.domain.openapi_importer.schema_model import EndpointSchema
from app.domain.test_case.schema import TestCaseCreateRequest
from app.domain.test_design.schema import TestIntent


class TestGenerator:
    """F023 pure function: ``TestIntent + (Operation, EndpointSchema) → TestCaseCreateRequest``.

    The two base-data objects serve distinct purposes:

    * ``Operation`` — F012 parser output. Owns the runtime request defaults
      (headers / query / body / body_type) that the happy_path intent may
      leave as ``None`` overrides.
    * ``EndpointSchema`` — F021 analyzer output. Owns the response schema
      metadata used for automatic json_path / header assertions.

    Passing them as keyword-only avoids the silent-bug risk of swapping the
    two positional arguments.
    """

    def intent_to_request(
        self,
        intent: TestIntent,
        *,
        operation: Operation,
        endpoint: EndpointSchema,
    ) -> TestCaseCreateRequest:
        """Single Intent → single ``TestCaseCreateRequest``.

        Steps (per SPEC §3.1):

        1. Derive headers / query / body / body_type from the operation
           defaults, then overlay each ``intent.*_override``.
        2. If ``strategy == "auth_missing"``: strip Authorization from
           the derived headers (F022 §5.2.6).
        3. Build assertions in this order:

           a. ``status_code`` from ``intent.expected_status_codes``
              (always, per F022 §4.1).
           b. ``intent.assertions`` (strategy-specific).
           c. Auto-assertions: only for ``happy_path`` (json_path from
              2xx response schema required fields + Content-Type header).

           Then de-duplicate by ``(type, operator, expected)`` triple.
        4. Truncate ``name`` to 200 chars (matches
           ``TestCaseBase.name`` max_length).
        """
        headers, query_params = self._derive_request_fields(
            intent=intent,
            operation=operation,
        )
        body, body_type = self._derive_body(
            intent=intent,
            operation=operation,
        )
        assertions = self._build_assertions(intent, endpoint)
        return TestCaseCreateRequest(
            name=intent.name[:200],
            method=intent.method,
            path=intent.path,
            headers=headers or None,
            query_params=query_params or None,
            body_type=body_type,
            body=body,
            assertions=assertions,
            timeout_seconds=30,
        )

    def intents_to_requests(
        self,
        intents: list[TestIntent],
        *,
        operation: Operation,
        endpoint: EndpointSchema,
    ) -> list[TestCaseCreateRequest]:
        """Bulk entry. Order is preserved (F022 priority order)."""
        return [
            self.intent_to_request(i, operation=operation, endpoint=endpoint)
            for i in intents
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_request_fields(
        *,
        intent: TestIntent,
        operation: Operation,
    ) -> tuple[dict, dict]:
        """Headers / query: operation defaults → intent overrides.

        ``auth_missing`` strategy strips ``Authorization`` regardless of
        whether it came from defaults or overrides.
        """
        headers: dict[str, str] = dict(operation.request_headers or {})
        if intent.headers_override:
            headers.update(intent.headers_override)
        query_params: dict[str, Any] = dict(operation.request_query or {})
        if intent.query_override:
            query_params.update(intent.query_override)
        if intent.strategy == "auth_missing":
            headers.pop("Authorization", None)
            headers.pop("authorization", None)
        return headers, query_params

    @staticmethod
    def _derive_body(
        *,
        intent: TestIntent,
        operation: Operation,
    ) -> tuple[Any, str]:
        """Body / body_type: intent override → operation default.

        ``body_type_override`` wins when present, else we fall back to
        the operation's runtime body_type (which mirrors F012 parser
        output: ``"json"`` if the spec had a JSON example, ``"none"`` if
        no request body).
        """
        body = (
            copy.deepcopy(intent.body_override)
            if intent.body_override is not None
            else operation.request_body
        )
        body_type = (
            intent.body_type_override
            if intent.body_type_override is not None
            else operation.request_body_type
        )
        return body, body_type

    @staticmethod
    def _build_assertions(
        intent: TestIntent,
        endpoint: EndpointSchema,
    ) -> list[dict[str, Any]]:
        """Build + de-duplicate assertions per SPEC §3.2.

        Order matters: status_code first (always), then intent.assertions
        (strategy-driven), then auto-assertions (happy_path only). After
        merging we de-duplicate by ``(type, operator, expected)`` triple.
        """
        assertions: list[dict[str, Any]] = []
        # (a) status_code from intent
        if intent.expected_status_codes:
            assertions.append(
                {
                    "type": "status_code",
                    "operator": (
                        "in" if intent.expected_status_mode == "any_of" else "not_in"
                    ),
                    "expected": list(intent.expected_status_codes),
                }
            )
        # (b) intent.assertions (strategy-specific; e.g. status_code again
        # for required_field_missing — de-dupe handles overlap)
        for a in intent.assertions:
            assertions.append(dict(a))
        # (c) auto-assertions: happy_path only (SPEC §3.2 + ADR-009 Q5)
        if intent.strategy == "happy_path":
            assertions.extend(TestGenerator._auto_json_path_assertions(endpoint))
            assertions.extend(TestGenerator._auto_header_assertions(endpoint))
        return TestGenerator._dedupe(assertions)

    @staticmethod
    def _auto_json_path_assertions(endpoint: EndpointSchema) -> list[dict[str, Any]]:
        """One ``json_path $.<field> exists`` per required field in the
        first 2xx response schema.

        Per ADR-009 Q5: silent skip when the response schema is absent.
        """
        out: list[dict[str, Any]] = []
        for resp in endpoint.responses:
            if not resp.status_code.startswith("2"):
                continue
            if resp.schema_model is None:
                continue
            for field_name in resp.schema_model.required:
                out.append(
                    {
                        "type": "json_path",
                        "operator": "exists",
                        "expected": f"$.{field_name}",
                    }
                )
            return out  # only first 2xx
        return out

    @staticmethod
    def _auto_header_assertions(endpoint: EndpointSchema) -> list[dict[str, Any]]:
        """One ``header Content-Type exists`` per 2xx response that has a
        declared content_type. Silent skip when absent (ADR-009 Q5)."""
        for resp in endpoint.responses:
            if not resp.status_code.startswith("2"):
                continue
            if resp.content_type:
                return [
                    {
                        "type": "header",
                        "operator": "exists",
                        "expected": "Content-Type",
                    }
                ]
            return []  # only first 2xx with content_type
        return []

    @staticmethod
    def _dedupe(
        assertions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """De-duplicate by ``(type, operator, expected-tuple)`` triple.

        ``expected`` may be a list of ints or strings; we coerce to tuple
        for hashability. Earlier assertions win (preserve order).
        """
        seen: set[tuple] = set()
        out: list[dict[str, Any]] = []
        for a in assertions:
            key = (
                a.get("type"),
                a.get("operator"),
                tuple(a.get("expected", [])),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(a)
        return out


__all__ = ["TestGenerator"]
