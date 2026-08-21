"""F022 happy_path strategy.

Per F022_SPEC §5.2.1: always emits exactly one TestIntent per endpoint;
not subject to per-strategy or hard caps.  This is the F012
byte-equivalent baseline.
"""
from __future__ import annotations
from typing import Optional

from app.domain.openapi_importer.schema_model import EndpointSchema
from app.domain.test_design.schema import TestIntent
from app.domain.test_design.strategies._helpers import (
    base_name,
    default_status_assertion,
    happy_path_body,
    make_intent_id,
    make_operation_id,
)


# Codes considered "success" for the default F012-equivalent assertion.
_HAPPY_PATH_CODES: list[int] = [200, 201, 202, 204]


class HappyPathStrategy:
    """Emit a single happy-path intent per endpoint.

    This strategy is **always** enabled (the engine enforces this) and
    its output count is **not** subject to ``max_per_op`` truncation
    (per F022_SPEC §5.2.1 / F022_PRECHECK §2.2 rule 5).
    """

    name: str = "happy_path"
    default_enabled: bool = True
    max_per_op: int = 1  # constant; not enforced

    def generate(self, endpoint: EndpointSchema) -> list[TestIntent]:
        body = happy_path_body(endpoint)
        body_type: Optional[str] = None
        if endpoint.request_body is not None and endpoint.request_body.content_type:
            body_type = "json" if "json" in endpoint.request_body.content_type else "raw"
        return [
            TestIntent(
                intent_id=make_intent_id(),
                strategy="happy_path",
                operation_id=make_operation_id(endpoint),
                method=endpoint.method,
                path=endpoint.path,
                name=(f"{base_name(endpoint)}: happy path")[:200],
                description="F022 happy-path baseline; F012-equivalent.",
                headers_override=None,
                query_override=None,
                body_override=body,
                body_type_override=body_type,
                assertions=[default_status_assertion(_HAPPY_PATH_CODES)],
                expected_status_codes=list(_HAPPY_PATH_CODES),
                expected_status_mode="any_of",
            )
        ]


__all__ = ["HappyPathStrategy"]