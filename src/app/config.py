"""Application configuration."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# A deliberately weak/placeholder secret value that MUST NOT be used in
# production. The startup-time check in ``validate_secrets`` rejects this
# value unless ``ENVIRONMENT`` is set to "test".
DEFAULT_INSECURE_JWT_SECRET = "your-secret-key-change-in-production"


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "Test Platform"
    APP_VERSION: str = "1.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # production | development | test

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_platform"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    # JWT
    # IMPORTANT: ``JWT_SECRET_KEY`` MUST be overridden in production. A weak
    # default is only allowed when ``ENVIRONMENT=test``.
    JWT_SECRET_KEY: str = DEFAULT_INSECURE_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "test-platform"
    JWT_AUDIENCE: str = "test-platform-api"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Login security
    # Maximum password length in BYTES (bcrypt silently truncates at 72 bytes).
    PASSWORD_MAX_BYTES: int = 72
    PASSWORD_MIN_LENGTH: int = 8
    # Failed attempts per (key, window) before the key is locked out.
    # In-memory; replace with Redis when going multi-instance.
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60
    LOGIN_LOCKOUT_SECONDS: int = 300

    # Test execution (F014 有限并发)
    # Maximum number of cases the TestRunner will execute in parallel
    # for a single Run. Capped server-side by the test environment's
    # asyncio capacity. Set to 1 to restore serial execution.
    TEST_RUN_MAX_CONCURRENCY: int = 4

    # OpenAPI batch import (F013 批量生成基础用例)
    # Maximum number of OpenAPI documents accepted in a single
    # ``POST /projects/{pid}/suites/{sid}/import/openapi?batch=true`` call.
    OPENAPI_BATCH_MAX_DOCS: int = 5
    # Maximum number of operations parsed from a single document in
    # a batch import. Beyond this limit the service raises
    # ``OPENAPI_BATCH_LIMIT_EXCEEDED`` rather than silently truncating.
    OPENAPI_BATCH_MAX_OPS_PER_DOC: int = 50


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()


def validate_secrets() -> None:
    """Validate security-critical configuration at startup.

    Raises ``RuntimeError`` if the process is started with a known-insecure
    default. Test environments are allowed to use the default value.
    """
    if settings.ENVIRONMENT == "test":
        return

    if settings.JWT_SECRET_KEY == DEFAULT_INSECURE_JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET_KEY is using the insecure default placeholder. "
            "Set a strong random secret via the JWT_SECRET_KEY environment "
            "variable before starting in a non-test environment.",
        )

    if len(settings.JWT_SECRET_KEY) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY must be at least 32 characters long. "
            f"Current length: {len(settings.JWT_SECRET_KEY)}.",
        )