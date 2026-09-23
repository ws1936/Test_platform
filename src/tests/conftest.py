"""Pytest fixtures for backend tests."""

from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "asyncio" in item.keywords:
            continue
        if asyncio.iscoroutinefunction(getattr(item, "function", None)):
            item.add_marker(pytest.mark.asyncio)


@pytest.fixture(autouse=True)
def _setup_test_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-secret-key-for-pytest-only-not-for-prod",
    )
    yield


@pytest.fixture(autouse=True)
def _reset_auth_state():
    from app.common.rate_limit import reset_for_tests
    from app.common.security import reset_blacklist_for_tests

    reset_blacklist_for_tests()
    reset_for_tests()
    yield
    reset_blacklist_for_tests()
    reset_for_tests()


@pytest_asyncio.fixture
async def db_engine():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from app.domain.environment.model import ApiEnvironment
    from app.domain.project.model import ApiProject
    from app.domain.role.model import Role
    from app.domain.suite.model import ApiSuite, ApiSuiteCase
    from app.domain.test_case.model import ApiTestCase
    from app.domain.test_run.model import ApiTestResult, ApiTestRun
    from app.domain.user.model import User
    from app.infrastructure.database.session import Base

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_db_between_tests(db_engine):
    yield
    from app.infrastructure.database.session import Base

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app(db_engine):
    from fastapi import FastAPI, Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.common.dependencies import get_role_service, get_user_service
    from app.common.exceptions import AppException
    from app.infrastructure.database.session import get_db
    from app.interfaces.http.auth_router import router as auth_router
    from app.interfaces.http.environment_router import environment_router
    from app.interfaces.http.environment_router import \
        project_router as environment_project_router
    from app.interfaces.http.openapi_importer_router import \
        import_router as openapi_importer_router
    from app.interfaces.http.project_router import router as project_router
    from app.interfaces.http.role_router import router as role_router
    from app.interfaces.http.suites import router as suites_router
    from app.interfaces.http.test_case_router import \
        case_router as test_case_case_router
    from app.interfaces.http.test_case_router import \
        collection_router as test_case_collection_router
    from app.interfaces.http.test_case_router import \
        project_router as test_case_project_router
    from app.interfaces.http.test_run_router import \
        case_router as test_run_case_router
    from app.interfaces.http.test_run_router import \
        result_router as test_run_result_router
    from app.interfaces.http.test_run_router import \
        run_resource_router as test_run_resource_router
    from app.interfaces.http.test_run_router import \
        run_router as test_run_project_router
    from app.interfaces.http.user_router import admin_router, me_router

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    test_app = FastAPI(title="Test App")
    # Expose the engine so back-office test helpers (e.g. token_version
    # bump) can connect to the same SQLite memory instance the request
    # lifecycle is using.
    test_app.state.db_engine = db_engine
    test_app.state.db_session_factory = session_factory

    @test_app.exception_handler(RequestValidationError)
    async def _validation_handler(request, exc):
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
    async def _app_exception_handler(request, exc):
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
    test_app.include_router(project_router, prefix="/api/v1")
    test_app.include_router(environment_project_router, prefix="/api/v1")
    test_app.include_router(environment_router, prefix="/api/v1")
    test_app.include_router(suites_router, prefix="/api/v1")
    test_app.include_router(test_case_collection_router, prefix="/api/v1")
    test_app.include_router(test_case_project_router, prefix="/api/v1")
    test_app.include_router(test_case_case_router, prefix="/api/v1")
    test_app.include_router(test_run_project_router, prefix="/api/v1")
    test_app.include_router(test_run_resource_router, prefix="/api/v1")
    test_app.include_router(test_run_result_router, prefix="/api/v1")
    test_app.include_router(test_run_case_router, prefix="/api/v1")
    test_app.include_router(openapi_importer_router, prefix="/api/v1")

    test_app.dependency_overrides[get_db] = _override_get_db
    yield test_app


@pytest_asyncio.fixture
async def client(app):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


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
    resp = await client.post("/api/v1/auth/register", json=user_payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["token"]["access_token"], body["token"]["refresh_token"]


@pytest_asyncio.fixture
async def create_test_cases(db_session):
    from uuid import UUID

    from app.domain.test_case.model import ApiTestCase

    async def _create(project_id, case_ids):
        normalized = [UUID(str(case_id)) for case_id in case_ids]
        for index, case_id in enumerate(normalized):
            db_session.add(
                ApiTestCase(
                    id=case_id,
                    project_id=UUID(str(project_id)),
                    name=f"case-{index}",
                    method="GET",
                    path=f"/case-{index}",
                    body_type="none",
                    timeout_seconds=30,
                    status=1,
                    sort_order=index,
                )
            )
        await db_session.commit()
        return normalized

    return _create


# ===========================================================================
# F023 fixture infrastructure (added 2026-09-23, see F023_SPEC.md §11)
# ===========================================================================
#
# Six fixtures that erase boilerplate otherwise duplicated in
# test_project_router / test_suite_router / test_environment_router /
# test_test_case_router / test_openapi_importer / test_authz_regressions.
# All existing fixtures above are preserved; new fixtures are additive.


@pytest.fixture
def auth_headers():
    """``auth_headers(token) -> {"Authorization": "Bearer <token>"}``.

    Factory fixture that returns a callable. Callers do::

        def test_x(client, auth_headers):
            resp = await client.post(
                "/...",
                json={...},
                headers=auth_headers(token),
            )

    Replaces the inline ``{"Authorization": f"Bearer {token}"}`` pattern
    that appears 30+ times across the test suite.
    """

    def _make(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest_asyncio.fixture
async def admin_user(client, user_payload):
    """First registered user — auto-promoted to superuser per F001 bootstrap.

    Returns a dict with keys:

    * ``user`` — response body ``user`` block (id, username, email, …)
    * ``access_token`` — JWT for Authorization header
    * ``refresh_token`` — for refresh-token tests
    * ``headers`` — ``{"Authorization": f"Bearer {access_token>"}``

    Distinct from ``registered_user`` (which returns a 2-tuple) — admin_user
    is the canonical "the bootstrap superuser" fixture for any test that
    needs the full user payload (e.g. authz_regressions needs ``user.id``).
    """
    resp = await client.post("/api/v1/auth/register", json=user_payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {
        "user": body["user"],
        "access_token": body["token"]["access_token"],
        "refresh_token": body["token"]["refresh_token"],
        "headers": {"Authorization": f"Bearer {body['token']['access_token']}"},
    }


@pytest_asyncio.fixture
async def member_user(client, admin_user):
    """A second registered user — NOT superuser (F001 invariant).

    Used by authz regressions where one user must NOT have access to
    another's project / suite / environment / case. Requires the
    bootstrap superuser's token to register (F001 rule: only superuser
    can register after the first user exists).

    Returns the same dict shape as :func:`admin_user`.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "member",
            "email": "member@example.com",
            "password": "TestPass123!",
            "nickname": "Member",
            "phone": "13900000000",
        },
        headers=admin_user["headers"],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {
        "user": body["user"],
        "access_token": body["token"]["access_token"],
        "refresh_token": body["token"]["refresh_token"],
        "headers": {"Authorization": f"Bearer {body['token']['access_token']}"},
    }


@pytest_asyncio.fixture
async def make_project(client):
    """``make_project(admin_h, name=None, description="") -> dict``.

    POSTs to ``/api/v1/projects`` with the admin token, returns the full
    project response body (``{"id": UUID, "name", "description", …}``).

    Default ``name`` is auto-generated (``P_<6-hex>``) to avoid 409
    conflicts across tests that create many projects in the same DB
    (the conftest's in-memory SQLite is reset per test, so this is
    belt-and-braces).
    """

    async def _create(
        admin_h: dict[str, str],
        name: str | None = None,
        description: str = "",
    ) -> dict:
        if name is None:
            name = f"P_{uuid.uuid4().hex[:6]}"
        resp = await client.post(
            "/api/v1/projects",
            json={"name": name, "description": description},
            headers=admin_h,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _create


@pytest_asyncio.fixture
async def make_environment(client):
    """``make_environment(admin_h, project_id, base_url=..., name=None, ...) -> dict``.

    POSTs to ``/api/v1/projects/{project_id}/environments``. Default
    ``name`` is ``E_<6-hex>``; default ``base_url`` is a benign
    ``https://api.test`` (engine-validatable but not actually contacted
    by router tests). ``headers`` / ``variables`` are optional.
    """

    async def _create(
        admin_h: dict[str, str],
        project_id,
        *,
        base_url: str = "https://api.test",
        name: str | None = None,
        headers: dict | None = None,
        variables: dict | None = None,
        is_default: bool = False,
    ) -> dict:
        if name is None:
            name = f"E_{uuid.uuid4().hex[:6]}"
        payload: dict = {
            "name": name,
            "base_url": base_url,
            "is_default": is_default,
        }
        if headers is not None:
            payload["headers"] = headers
        if variables is not None:
            payload["variables"] = variables
        resp = await client.post(
            f"/api/v1/projects/{project_id}/environments",
            json=payload,
            headers=admin_h,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _create


@pytest_asyncio.fixture
async def make_suite(client):
    """``make_suite(admin_h, project_id, name=None, description="") -> dict``.

    POSTs to ``/api/v1/projects/{project_id}/suites``. Default ``name``
    is ``S_<6-hex>``.
    """

    async def _create(
        admin_h: dict[str, str],
        project_id,
        *,
        name: str | None = None,
        description: str = "",
    ) -> dict:
        if name is None:
            name = f"S_{uuid.uuid4().hex[:6]}"
        resp = await client.post(
            f"/api/v1/projects/{project_id}/suites",
            json={"name": name, "description": description},
            headers=admin_h,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _create
