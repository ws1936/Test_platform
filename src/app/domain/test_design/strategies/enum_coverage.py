"""F022 enum_coverage strategy.

Per F022_SPEC §5.2.3: emit one intent per (enum_field, enum_value).
Truncation is performed centrally by ``TestDesignEngine``.
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


_HAPPY_PATH_CODES: list[int] = [200, 201]


class EnumCoverageStrategy:
    name: str = "enum_coverage"
    default_enabled: bool = False

    def __init__(self, max_per_op: int = 10) -> None:
        # Cap is informational; engine applies truncation (F022_SPEC §6.1).
        self.max_per_op = max_per_op

    def generate(self, endpoint: EndpointSchema) -> list[TestIntent]:
        sm = _request_schema(endpoint)
        if sm is None or not sm.properties:
            return []
        body_template = happy_path_body(endpoint)
        if not isinstance(body_template, dict):
            return []
        intents: list[TestIntent] = []
        for field_name, field_sm in sm.properties.items():
            enum_values = field_sm.enum or []
            for value in enum_values:
                mutated = copy.deepcopy(body_template)
                mutated[field_name] = value
                intents.append(
                    TestIntent(
                        intent_id=make_intent_id(),
                        strategy="enum_coverage",
                        operation_id=make_operation_id(endpoint),
                        method=endpoint.method,
                        path=endpoint.path,
                        name=(
                            f"{base_name(endpoint)}: enum '{field_name}' = '{value}'"
                        )[:200],
                        description=(
                            f"Cover enum value {value!r} of field '{field_name}'."
                        ),
                        headers_override=None,
                        query_override=None,
                        body_override=mutated,
                        body_type_override="json",
                        assertions=[default_status_assertion(_HAPPY_PATH_CODES)],
                        expected_status_codes=list(_HAPPY_PATH_CODES),
                        expected_status_mode="any_of",
                    )
                )
        return intents


def _request_schema(endpoint: EndpointSchema) -> SchemaModel | None:
    if endpoint.request_body is None:
        return None
    return endpoint.request_body.schema_model


__all__ = ["EnumCoverageStrategy"]