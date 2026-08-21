"""F022 boundary_min_max strategy.

Per F022_SPEC §5.2.4: emit 6 boundary intents per numeric field with
explicit bounds — ``min-1, min, min+1, max-1, max, max+1``.  In-bounds
values expect happy codes; out-of-bounds values expect 4xx.

Only fields with ``type ∈ {integer, number}`` AND both ``minimum`` and
``maximum`` set are eligible (per the SPEC).  Truncation is performed
centrally by ``TestDesignEngine``.
"""
from __future__ import annotations
import copy
from typing import Any, Optional

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
_BAD_REQUEST_CODES: list[int] = [400, 422]
_NUMERIC_TYPES = {"integer", "number"}


def _bounds(sm: SchemaModel) -> Optional[tuple[float, float]]:
    if sm.type not in _NUMERIC_TYPES:
        return None
    if sm.minimum is None or sm.maximum is None:
        return None
    return float(sm.minimum), float(sm.maximum)


def _is_in_bounds(value: float, lo: float, hi: float) -> bool:
    return lo <= value <= hi


class BoundaryMinMaxStrategy:
    name: str = "boundary_min_max"
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
            bounds = _bounds(field_sm)
            if bounds is None:
                continue
            lo, hi = bounds
            candidates = [lo - 1, lo, lo + 1, hi - 1, hi, hi + 1]
            for value in candidates:
                mutated = copy.deepcopy(body_template)
                if field_sm.type == "integer" and float(value).is_integer():
                    mutated[field_name] = int(value)
                else:
                    mutated[field_name] = value
                in_bounds = _is_in_bounds(float(value), lo, hi)
                expected = _HAPPY_PATH_CODES if in_bounds else _BAD_REQUEST_CODES
                intents.append(
                    TestIntent(
                        intent_id=make_intent_id(),
                        strategy="boundary_min_max",
                        operation_id=make_operation_id(endpoint),
                        method=endpoint.method,
                        path=endpoint.path,
                        name=(
                            f"{base_name(endpoint)}: boundary {field_name}={value}"
                        )[:200],
                        description=(
                            f"Boundary value {value} on field '{field_name}' "
                            f"(range [{lo}, {hi}])."
                        ),
                        headers_override=None,
                        query_override=None,
                        body_override=mutated,
                        body_type_override="json",
                        assertions=[default_status_assertion(expected)],
                        expected_status_codes=list(expected),
                        expected_status_mode="any_of",
                    )
                )
        return intents


def _request_schema(endpoint: EndpointSchema) -> SchemaModel | None:
    if endpoint.request_body is None:
        return None
    return endpoint.request_body.schema_model


__all__ = ["BoundaryMinMaxStrategy"]