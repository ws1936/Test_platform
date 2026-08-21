"""F022 format_invalid strategy.

Per F022_SPEC §5.2.5: emit one intent per format-annotated string
field, with an obviously-invalid placeholder.  Truncation is performed
centrally by ``TestDesignEngine``.

Supported formats: ``email``, ``uuid``, ``date-time``, ``uri``,
``ipv4``, ``ipv6`` (per F022_PRECHECK §12 / F022_SPEC §5.2.5).
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
_SUPPORTED_FORMATS = {"email", "uuid", "date-time", "uri", "ipv4", "ipv6"}

# Per-format obviously-invalid value placeholders.  These are *deliberately*
# malformed so the validator should reject them; the strategy does not
# attempt to enumerate every invalid shape — one per field is enough.
_INVALID_BY_FORMAT: dict[str, str] = {
    "email": "not-a-valid-email",
    "uuid": "not-a-uuid",
    "date-time": "not-a-date-time",
    "uri": "not a uri",
    "ipv4": "999.999.999.999",
    "ipv6": "not::an::ipv6::address",
}


class FormatInvalidStrategy:
    name: str = "format_invalid"
    default_enabled: bool = False

    def __init__(self, max_per_op: int = 5) -> None:
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
            if field_sm.type != "string":
                continue
            if field_sm.format not in _SUPPORTED_FORMATS:
                continue
            invalid_value = _INVALID_BY_FORMAT[field_sm.format]
            mutated = copy.deepcopy(body_template)
            mutated[field_name] = invalid_value
            intents.append(
                TestIntent(
                    intent_id=make_intent_id(),
                    strategy="format_invalid",
                    operation_id=make_operation_id(endpoint),
                    method=endpoint.method,
                    path=endpoint.path,
                    name=(
                        f"{base_name(endpoint)}: invalid format on {field_name}"
                    )[:200],
                    description=(
                        f"Submit an obviously-invalid {field_sm.format} value for '{field_name}'."
                    ),
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


__all__ = ["FormatInvalidStrategy"]