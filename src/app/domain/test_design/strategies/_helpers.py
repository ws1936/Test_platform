"""F022 shared helpers for strategy implementations.

Common utilities for building TestIntent objects with consistent IDs
and naming.  Kept private to ``strategies/`` to avoid leaking internal
helper surface.
"""
from __future__ import annotations
import copy
from typing import Any, Optional
from uuid import uuid4

from app.domain.openapi_importer.schema_model import EndpointSchema
from app.domain.test_design.schema import TestIntent


def make_intent_id() -> str:
    """Per-intent UUID4 hex; unique within the engine invocation."""
    return uuid4().hex


def make_operation_id(endpoint: EndpointSchema) -> str:
    """Stable per-operation identifier (used in TestIntent.operation_id)."""
    return f"{endpoint.method} {endpoint.path}"


def base_name(endpoint: EndpointSchema) -> str:
    """Human-friendly base name; defaults to ``"<method> <path>"`` if missing."""
    return endpoint.summary or f"{endpoint.method} {endpoint.path}"


def default_status_assertion(codes: list[int]) -> dict[str, Any]:
    """Standard status-code assertion dict (F009-compatible shape)."""
    return {"type": "status_code", "operator": "in", "expected": codes}


def happy_path_body(endpoint: EndpointSchema) -> Any:
    """Extract a representative body from request_body schema's first example.

    Falls back to ``{}`` when no example / no request body.  The F022
    happy path intentionally does NOT clone F012 parser's body assembly
    so F022 remains independent of F012's internal dataclass fields.
    """
    if endpoint.request_body is None or endpoint.request_body.schema_model is None:
        return None
    sm = endpoint.request_body.schema_model
    if sm.example is not None:
        return copy.deepcopy(sm.example)
    if sm.properties:
        # Build a minimal body with required fields set to their example or None.
        body: dict[str, Any] = {}
        for prop_name, prop_sm in sm.properties.items():
            if prop_name in sm.required:
                body[prop_name] = (
                    copy.deepcopy(prop_sm.example)
                    if prop_sm.example is not None
                    else _default_for_type(prop_sm.type)
                )
        return body
    return {}


def _default_for_type(type_name: Optional[str]) -> Any:
    """Best-effort placeholder for an unspecified type."""
    return {
        "string": "string",
        "integer": 0,
        "number": 0.0,
        "boolean": False,
        "array": [],
        "object": {},
    }.get(type_name or "", None)


__all__ = [
    "base_name",
    "default_status_assertion",
    "happy_path_body",
    "make_intent_id",
    "make_operation_id",
]