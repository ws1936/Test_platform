"""F022 auth_missing strategy.

Per F022_SPEC §5.2.6: emit at most one intent when the endpoint
declares ``security`` requirements.  The intent removes the
``Authorization`` header (the most common security header); richer
scheme handling (OAuth2 / APIKey) is explicitly deferred to F022+1
(per F022_SPEC §12).

The cap is always 1 (per F022_PRECHECK §2.1); F023 layer may further
restrict via ``?design=schema`` query semantics (ADR-009).
"""
from __future__ import annotations
from typing import Any

from app.domain.openapi_importer.schema_model import EndpointSchema
from app.domain.test_design.schema import TestIntent
from app.domain.test_design.strategies._helpers import (
    base_name,
    default_status_assertion,
    make_intent_id,
    make_operation_id,
)


_UNAUTHORIZED_CODES: list[int] = [401]


class AuthMissingStrategy:
    name: str = "auth_missing"
    default_enabled: bool = False

    def __init__(self, max_per_op: int = 1) -> None:
        # Cap is always 1; constructor accepts the kwarg only so it can
        # be wired through the engine's settings indirection.
        self.max_per_op = 1

    def generate(self, endpoint: EndpointSchema) -> list[TestIntent]:
        if not endpoint.security:
            return []
        return [
            TestIntent(
                intent_id=make_intent_id(),
                strategy="auth_missing",
                operation_id=make_operation_id(endpoint),
                method=endpoint.method,
                path=endpoint.path,
                name=(f"{base_name(endpoint)}: missing auth")[:200],
                description=(
                    "Remove the Authorization header to provoke 401."
                ),
                headers_override={},  # explicit empty set = drop Authorization
                query_override=None,
                body_override=None,
                body_type_override=None,
                assertions=[default_status_assertion(_UNAUTHORIZED_CODES)],
                expected_status_codes=list(_UNAUTHORIZED_CODES),
                expected_status_mode="any_of",
            )
        ]


__all__ = ["AuthMissingStrategy"]