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


class OpenApiIntentLimitExceededError(BadRequestException):
    """Raised when an F023 design="schema" preview/commit exceeds the
    per-operation intent cap.

    Triggered when ``?design=schema`` produces more than
    ``settings.generator_max_intents_per_operation`` intents for a single
    OpenAPI operation. Per ADR-009 decision 5: abort the entire batch
    (not per-operation isolation as in F013) because intent overflow is a
    platform-protection guard, not a data error.

    Per ERROR_CODE.md §5.1: HTTP 400 with business code
    ``GENERATOR_INTENT_LIMIT_EXCEEDED``.
    """

    def __init__(
        self,
        message: str = ("Generator intent cap exceeded for one or more operations"),
        details=None,
    ):
        super().__init__(message=message, details=details)
        self.code = "GENERATOR_INTENT_LIMIT_EXCEEDED"
