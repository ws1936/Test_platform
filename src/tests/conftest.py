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
    """Override DATABASE_URL to use in-memory SQLite BEFORE app imports."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-pytest")
    yield


# === Database fixture ===

@pytest_asyncio.fixture
async def db_engine():
    """Create a fresh in-memory SQLite engine per test."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.infrastructure.database.session import Base
    # Import models so they register on Base.metadata
    from app.domain.user.model import User  # noqa: F401
    from app.domain.role.model import Role  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


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
    from fastapi import FastAPI
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.common.dependencies import get_user_service, get_role_service
    from app.infrastructure.database.session import get_db
    from app.interfaces.http.auth_router import router as auth_router
    from app.interfaces.http.user_router import admin_router, me_router
    from app.interfaces.http.role_router import router as role_router

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    test_app = FastAPI(title="Test App")
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
