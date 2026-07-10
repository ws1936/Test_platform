"""Unified API response wrappers.

Per AI_RULES §8, all successful responses must use:
    {"code": 0, "message": "success", "data": ...}

This module provides:
- Response envelope helpers
- A custom JSONResponse that auto-wraps data into the envelope
- A Pydantic envelope model for OpenAPI documentation
"""

from typing import Any, Optional

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """Standard API response envelope."""

    code: int = Field(default=0, description="0=success, others=error")
    message: str = Field(default="success", description="Human readable message")
    data: Optional[Any] = Field(default=None, description="Response payload")


class ErrorResponse(BaseModel):
    """Standard API error response envelope."""

    code: int = Field(description="Error code (non-zero)")
    message: str = Field(description="Error description")
    details: Optional[dict[str, Any]] = Field(default=None, description="Extra info")


def success_response(
    data: Any = None,
    message: str = "success",
    status_code: int = 200,
) -> JSONResponse:
    """Build a successful unified API response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "code": 0,
            "message": message,
            "data": jsonable_encoder(data),
        },
    )


def error_response(
    code: int,
    message: str,
    status_code: int = 400,
    details: Optional[dict[str, Any]] = None,
) -> JSONResponse:
    """Build an error unified API response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details or {},
        },
    )
