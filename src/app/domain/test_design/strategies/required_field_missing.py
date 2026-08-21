"""F022 required_field_missing strategy.

Per F022_SPEC §5.2.2: emit one intent per missing required field.
Truncation is performed centrally by ``TestDesignEngine`` — this
strategy emits *all* eligible intents so the engine can apply both
per-strategy and global caps consistently.
"""
from __future__ import annotations
import copy
from typing import Any

from app.domain.openapi_importer.schema_model import EndpointSchema, SchemaModel
from app.domain.test_design.schema import TestIntent
from app.domain.test_design.strategies._helpers import (
    base_name,
    default_status_assertion,
    happy_path_body,
    make_intent_id,
    make_operation_id,
)


_BAD_REQUEST_CODES: list[int] = [400, 422]


class RequiredFieldMissingStrategy:
    name: str = "required_field_missing"
    default_enabled: bool = False

    def __init__(self, max_per_op: int = 5) -> None:
        # Cap is informational here; the engine applies the truncation
        # uniformly (F022_SPEC §6.1).
        self.max_per_op = max_per_op

    def generate(self, endpoint: EndpointSchema) -> list[TestIntent]:
        sm = _request_schema(endpoint)
        if sm is None or not sm.required:
            return []
        body_template = happy_path_body(endpoint) or {}
        if not isinstance(body_template, dict):
            return []
        intents: list[TestIntent] = []
        for field_name in sm.required:
            mutated = copy.deepcopy(body_template)
            mutated.pop(field_name, None)
            intents.append(
                TestIntent(
                    intent_id=make_intent_id(),
                    strategy="required_field_missing",
                    operation_id=make_operation_id(endpoint),
                    method=endpoint.method,
                    path=endpoint.path,
                    name=(f"{base_name(endpoint)}: missing required field '{field_name}'")[:200],
                    description=f"Omit required field '{field_name}' to provoke 4xx.",
                    headers_override=None,
                    query_override=None,
                    body_override=mutated,
                    body_type_override="json",
                    assertions=[default_status_assertion(_BAD_REQUEST_CODES)],
                    expected_status_codes=list(_BAD_REQUEST_CODES),
                    expected_status_mode="any_of",
                )
            )
        return intents


def _request_schema(endpoint: EndpointSchema) -> SchemaModel | None:
    if endpoint.request_body is None:
        return None
    return endpoint.request_body.schema_model


__all__ = ["RequiredFieldMissingStrategy"]