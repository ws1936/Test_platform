"""Common exceptions for the application.

Business error codes are defined per ``docs/03-api/ERROR_CODE.md``.
The HTTP status + business code mapping is enforced here so that
Router code does not have to translate generic errors manually.
"""

from typing import Any, Optional


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found", details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details,
        )


class UnauthorizedException(AppException):
    """Unauthorized access exception."""

    def __init__(self, message: str = "Unauthorized", details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
            details=details,
        )


class ForbiddenException(AppException):
    """Forbidden access exception."""

    def __init__(self, message: str = "Forbidden", details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            details=details,
        )


class BadRequestException(AppException):
    """Bad request exception."""

    def __init__(self, message: str = "Bad request", details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="BAD_REQUEST",
            status_code=400,
            details=details,
        )


class ConflictException(AppException):
    """Conflict exception (e.g., duplicate resource)."""

    def __init__(self, message: str = "Conflict", details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details=details,
        )


# === Authentication / User business errors (ERROR_CODE.md §4) ===

# 20001 - wrong credentials
class CredentialsInvalidException(UnauthorizedException):
    """Invalid email or password."""

    def __init__(
        self,
        message: str = "Invalid email or password",
        details: Optional[dict] = None,
    ):
        super().__init__(message=message, details=details)
        self.code = "INVALID_CREDENTIALS"  # business code 20001


# 20002 - account disabled
class AccountDisabledException(ForbiddenException):
    """User account has been disabled."""

    def __init__(
        self,
        message: str = "User account is disabled",
        details: Optional[dict] = None,
    ):
        super().__init__(message=message, details=details)
        self.code = "ACCOUNT_DISABLED"  # business code 20002


# 20003 - username already exists
class UsernameAlreadyExistsException(ConflictException):
    """Username is already taken."""

    def __init__(
        self,
        message: str = "Username is already taken",
        details: Optional[dict] = None,
    ):
        super().__init__(message=message, details=details)
        self.code = "USERNAME_TAKEN"  # business code 20003


# 20004 - email already exists
class EmailAlreadyExistsException(ConflictException):
    """Email is already registered."""

    def __init__(
        self,
        message: str = "Email is already registered",
        details: Optional[dict] = None,
    ):
        super().__init__(message=message, details=details)
        self.code = "EMAIL_TAKEN"  # business code 20004


# 20005 - user not found
class UserNotFoundException(NotFoundException):
    """User does not exist."""

    def __init__(
        self,
        message: str = "User not found",
        details: Optional[dict] = None,
    ):
        super().__init__(message=message, details=details)
        self.code = "USER_NOT_FOUND"  # business code 20005


# 20006 - wrong old password during password change
class IncorrectOldPasswordException(BadRequestException):
    """The provided old password does not match the current password."""

    def __init__(
        self,
        message: str = "Old password is incorrect",
        details: Optional[dict] = None,
    ):
        super().__init__(message=message, details=details)
        self.code = "INCORRECT_OLD_PASSWORD"  # business code 20006


# Generic 401 for unauthenticated requests (11001/11002)
class TokenInvalidException(UnauthorizedException):
    """Access token is missing, malformed, expired or revoked."""

    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[dict] = None,
    ):
        super().__init__(message=message, details=details)
        self.code = "TOKEN_INVALID"  # business code 11002


# Rate limit / brute force protection
class TooManyRequestsException(AppException):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Too many requests, please try again later",
        details: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            code="TOO_MANY_REQUESTS",
            status_code=429,
            details=details,
        )