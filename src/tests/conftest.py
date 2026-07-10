"""Pytest fixtures for backend tests.

Uses an in-memory SQLite database via aiosqlite, overriding the production
PostgreSQL engine. The test app is created lazily so model imports are
deferred until first use.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio


# === Pytest configuration ===

def pytest_collection_modifyitems(config, items):
    """Mark async tests automatically."""
    for item in items:
        if "asyncio" in item.keywords:
            continue
        if asyncio.iscoroutinefunction(getattr(item, "function", None)):
            item.add_marker(pytest.mark.asyncio)


# === Event loop fixture ===

@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop so async fixtures can share state."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# === Test environment setup ===

@pytest.fixture(autouse=True)
def _setup_test_env(monkeypatch):
    """Override configuration for tests BEFORE app imports."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    # Use a 32+ char secret so ``validate_secrets`` is happy if invoked.
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-secret-key-for-pytest-only-not-for-prod",
    )
    yield


@pytest.fixture(autouse=True)
def _reset_auth_state():
    """Clear the in-memory token blacklist & rate-limiters between tests."""
    from app.common.rate_limit import reset_for_tests
    from app.common.security import reset_blacklist_for_tests

    reset_blacklist_for_tests()
    reset_for_tests()
    yield
    reset_blacklist_for_tests()
    reset_for_tests()


# === Database fixture ===

@pytest_asyncio.fixture
async def db_engine():
    """Create a fresh in-memory SQLite engine per test.

    We use ``StaticPool`` + a single shared connection so every session
    sees the same in-memory database. Tables are recreated between
    tests via ``db_clean``.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from app.infrastructure.database.session import Base
    # Import models so they register on Base.metadata
    from app.domain.user.model import User  # noqa: F401
    from app.domain.role.model import Role  # noqa: F401

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_db_between_tests(db_engine):
    """Drop all tables after every test for isolation."""
    yield
    from app.infrastructure.database.session import Base

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator:
    """Provide a transactional session that rolls back at end of test."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


# === Test app + client fixtures ===

@pytest_asyncio.fixture
async def app(db_engine):
    """Build a FastAPI app with overridden DB dependency."""
    from fastapi import FastAPI, Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.common.dependencies import get_user_service, get_role_service
    from app.common.exceptions import AppException
    from app.infrastructure.database.session import get_db
    from app.interfaces.http.auth_router import router as auth_router
    from app.interfaces.http.user_router import admin_router, me_router
    from app.interfaces.http.role_router import router as role_router

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    test_app = FastAPI(title="Test App")

    # Mirror ``main.py``'s exception handlers so tests exercise the
    # same error responses that production will emit.
    @test_app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        errors = [
            {
                "field": ".".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
            },
        )

    @test_app.exception_handler(AppException)
    async def _app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    test_app.include_router(auth_router, prefix="/api/v1")
    test_app.include_router(me_router, prefix="/api/v1")
    test_app.include_router(admin_router, prefix="/api/v1")
    test_app.include_router(role_router, prefix="/api/v1")

    test_app.dependency_overrides[get_db] = _override_get_db
    yield test_app


@pytest_asyncio.fixture
async def client(app):
    """Async HTTP test client (httpx)."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# === Common payload helpers ===

@pytest.fixture
def user_payload() -> dict:
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "TestPass123!",
        "nickname": "Tester",
        "phone": "13800000000",
    }


@pytest_asyncio.fixture
async def registered_user(client, user_payload):
    """Register a user and return ``(access_token, refresh_token)``."""
    resp = await client.post("/api/v1/auth/register", json=user_payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["token"]["access_token"], body["token"]["refresh_token"]