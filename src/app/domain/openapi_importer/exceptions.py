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


class OpenApiBatchLimitExceededError(BadRequestException):
    """Raised when an F013 batch import exceeds configured per-doc limits.

    Triggered when a single OpenAPI document in a batch parses to more
    than ``settings.OPENAPI_BATCH_MAX_OPS_PER_DOC`` operations.

    Per ERROR_CODE.md §5.1: HTTP 400 with business code
    ``OPENAPI_BATCH_LIMIT_EXCEEDED``. Documents count limits
    (``OPENAPI_BATCH_MAX_DOCS``) are caught earlier by the request
    schema validator and surface as 422 VALIDATION_ERROR.
    """

    def __init__(
        self,
        message: str = "OpenAPI batch import exceeded per-document limit",
        details=None,
    ):
        super().__init__(message=message, details=details)
        self.code = "OPENAPI_BATCH_LIMIT_EXCEEDED"
