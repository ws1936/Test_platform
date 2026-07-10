"""Security utilities for JWT and password hashing.

Design notes:
- JWTs include ``jti`` (unique id), ``iss``/``aud`` and ``nbf`` claims to
  prevent cross-service replay and to allow precise revocation.
- The token blacklist is keyed by ``jti`` (not the entire token) and
  stores an expiry timestamp; expired entries are evicted lazily.
- The blacklist is in-memory; production deployments behind multiple
  workers MUST replace this with Redis (see ``AI_RULES.md`` §4.4).
- Passwords are validated against ``settings.PASSWORD_MAX_BYTES`` to
  avoid silent bcrypt truncation at 72 bytes.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import bcrypt
from jose import JWTError, jwt

from app.config import settings


logger = logging.getLogger(__name__)


# bcrypt itself is used directly instead of passlib because passlib 1.7.4
# is incompatible with bcrypt >= 4.1 (``__about__`` attribute was
# removed). Direct usage also avoids silent failures during
# CryptContext initialisation in tests.
_BCRYPT_MAX_BYTES = 72
_BCRYPT_DEFAULT_ROUNDS = 12


# Token blacklist: jti -> absolute expiry epoch seconds.
# An entry is removed automatically once the underlying token has expired.
_blacklist: dict[str, float] = {}
_blacklist_lock = threading.Lock()


def _evict_expired_blacklist_entries(now: Optional[float] = None) -> None:
    """Drop blacklist entries whose token has already expired."""
    if now is None:
        now = time.time()
    expired = [jti for jti, exp in _blacklist.items() if exp <= now]
    for jti in expired:
        _blacklist.pop(jti, None)


def reset_blacklist_for_tests() -> None:
    """Clear the in-memory blacklist. Tests-only."""
    with _blacklist_lock:
        _blacklist.clear()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash.

    ``plain_password`` is truncated to 72 bytes to match bcrypt's
    historical behaviour. ``validate_password_strength`` should be
    called upstream to reject overly long passwords before they reach
    this function.
    """
    if not plain_password or not hashed_password:
        return False
    pwd_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with a fresh salt."""
    pwd_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    salt = bcrypt.gensalt(rounds=_BCRYPT_DEFAULT_ROUNDS)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def validate_password_strength(password: str) -> Optional[str]:
    """Return an error message if the password is too long for bcrypt.

    bcrypt silently truncates passwords at 72 bytes, which would
    otherwise let two distinct passwords hash to the same value. We
    reject anything longer up-front so behaviour is explicit.
    """
    if password is None:
        return "Password is required"
    encoded_len = len(password.encode("utf-8"))
    if encoded_len > settings.PASSWORD_MAX_BYTES:
        return (
            f"Password too long: {encoded_len} bytes "
            f"(max {settings.PASSWORD_MAX_BYTES})."
        )
    return None


def _build_token_claims(
    subject: str | UUID,
    token_type: str,
    expires_delta: timedelta,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the JWT claims dictionary shared by access/refresh tokens."""
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    claims: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "nbf": now,
        "exp": expire,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": token_type,
        "jti": uuid4().hex,
    }
    if extra:
        claims.update(extra)
    return claims


def create_access_token(
    subject: str | UUID,
    expires_delta: Optional[timedelta] = None,
    token_version: int = 0,
) -> str:
    """Create an access token.

    ``token_version`` lets callers bind a token to a specific user
    credential version so password changes / logouts-everywhere can
    invalidate older tokens without consulting the blacklist.
    """
    delta = expires_delta or timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    claims = _build_token_claims(subject, "access", delta, extra={"v": token_version})
    return jwt.encode(
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    subject: str | UUID,
    expires_delta: Optional[timedelta] = None,
    token_version: int = 0,
) -> str:
    """Create a refresh token (longer lived)."""
    delta = expires_delta or timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    )
    claims = _build_token_claims(
        subject, "refresh", delta, extra={"v": token_version},
    )
    return jwt.encode(
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or is otherwise invalid."""


def decode_token(
    token: str,
    expected_type: Optional[str] = None,
) -> dict[str, Any]:
    """Decode and verify a JWT.

    Raises ``TokenError`` on any failure (malformed, expired, bad
    signature, wrong issuer/audience, wrong type, blacklisted).
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={"require": ["exp", "iat", "nbf", "sub", "jti"]},
        )
    except JWTError as exc:
        raise TokenError(f"Invalid token: {exc}") from exc

    jti = payload.get("jti")
    if jti is None:
        raise TokenError("Token missing jti claim")

    if is_token_blacklisted(jti):
        raise TokenError("Token has been revoked")

    if expected_type is not None and payload.get("type") != expected_type:
        raise TokenError(f"Expected {expected_type} token")

    return payload


def blacklist_token(token: str) -> None:
    """Add a token to the blacklist (used for logout).

    The token MUST be a fully-formed JWT; its ``jti`` and ``exp`` claims
    are used for storage so the entry can self-expire.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={"verify_exp": True},
        )
    except JWTError:
        # Silently ignore garbage tokens; the blacklist only stores valid jtis.
        logger.warning("Attempted to blacklist a malformed token")
        return

    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or exp is None:
        return

    with _blacklist_lock:
        _evict_expired_blacklist_entries()
        _blacklist[jti] = float(exp)


def is_token_blacklisted(jti: str) -> bool:
    """Check whether a ``jti`` is currently blacklisted.

    Expired entries are evicted lazily on lookup.
    """
    if not jti:
        return False
    now = time.time()
    with _blacklist_lock:
        if jti in _blacklist and _blacklist[jti] > now:
            return True
        # Stale entry — clean it up.
        _blacklist.pop(jti, None)
        return False


def create_token_pair(
    user_id: UUID,
    token_version: int = 0,
) -> dict[str, Any]:
    """Create both access and refresh tokens."""
    access_token = create_access_token(
        subject=user_id, token_version=token_version,
    )
    refresh_token = create_refresh_token(
        subject=user_id, token_version=token_version,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }