"""Custom exceptions for F012 OpenAPI importer."""
from __future__ import annotations
from app.common.exceptions import BadRequestException

class OpenApiParseError(BadRequestException):
    def __init__(self, message="Invalid OpenAPI document", details=None):
        super().__init__(message=message, details=details)
        self.code = "OPENAPI_PARSE_ERROR"

class OpenApiFetchError(BadRequestException):
    def __init__(self, message="OpenAPI fetch failed", details=None):
        super().__init__(message=message, details=details)
        self.code = "OPENAPI_FETCH_ERROR"

class OpenApiImportConflictError(BadRequestException):
    def __init__(self, message="Import conflict", details=None):
        super().__init__(message=message, details=details)
        self.code = "OPENAPI_IMPORT_CONFLICT"
