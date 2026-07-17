"""Unit tests for :class:`TestCaseService` (F007).

Focus is on the business rules that live in the service layer — the
HTTP layer is exercised separately by ``test_test_case_router.py``.

Covered rules:

* Cross-project isolation: a user cannot reach test cases of a
  project they don't own.
* ``enabled`` round-trip: ``status`` (int) is mapped to ``enabled``
  (bool) on the wire.
* ``sort_order`` is monotonically allocated per project.
* ``delete_test_case`` cascades to ``api_suite_cases`` rows
  (the SQLite engine must enable ``PRAGMA foreign_keys=ON``).
* ``update_test_case`` only touches fields present in the payload
  (partial update).
* ``list_suite_cases`` excludes free-floating cases.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker


if TYPE_CHECKING:
    from app.domain.project.model import ApiProject
    from app.domain.user.model import User




# === Fixtures local to this module ===


@pytest_asyncio.fixture
async def service_db_engine():
    """Standalone SQLite engine for direct Service-level tests.

    Mirrors ``test_suite_service.py``'s pattern. ``PRAGMA
    foreign_keys=ON`` is required so ``ON DELETE CASCADE`` on
    ``api_suite_cases.test_case_id`` actually fires during the
    cascade test.
    """
    from sqlalchemy import event
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

    from app.domain.environment.model import ApiEnvironment  # noqa: F401
    from app.domain.project.model import ApiProject  # noqa: F401
    from app.domain.role.model import Role  # noqa: F401
    from app.domain.test_case.model import ApiTestCase  # noqa: F401
    from app.domain.suite.model import ApiSuite, ApiSuiteCase  # noqa: F401,E501
    from app.domain.user.model import User  # noqa: F401
    from app.infrastructure.database.session import Base

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def service_db_session(service_db_engine) -> AsyncGenerator:
    session_factory = async_sessionmaker(service_db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


# === Helpers (mirror test_environment_service.py's helpers) ===


async def _create_user_with_role(
    session,
    *,
    username: str,
    email: str,
    is_superuser: bool = False,
) -> "User":
    from app.common.security import hash_password
    from app.domain.role.model import Role
    from app.domain.user.model import User

    role = Role(
        id=uuid.uuid4(),
        name=f"role_{uuid.uuid4().hex[:8]}",
        description="test role",
        permissions=None,
        is_system=False,
    )
    session.add(role)
    await session.flush()

    user = User(
        id=uuid.uuid4(),
        username=username,
        email=email,
        hashed_password=hash_password("TestPass123!"),
        nickname=username.capitalize(),
        phone="13800000000",
        status=1,
        role_id=role.id,
        is_superuser=is_superuser,
    )
    session.add(user)
    await session.commit()
    return user


async def _create_project(session, *, owner) -> "ApiProject":
    from app.domain.project.model import ApiProject

    project = ApiProject(
        id=uuid.uuid4(),
        name=f"Project {uuid.uuid4().hex[:6]}",
        description="svc test project",
        owner_id=owner.id,
    )
    session.add(project)
    await session.commit()
    return project


async def _create_suite(session, *, project, name: str = "smoke"):
    from app.domain.suite.model import ApiSuite

    suite = ApiSuite(
        id=uuid.uuid4(),
        project_id=project.id,
        name=name,
        description="svc suite",
        sort_order=0,
    )
    session.add(suite)
    await session.commit()
    return suite


def _make_create_request(**overrides):
    """Build a ``TestCaseCreateRequest`` directly (no HTTP)."""
    from app.domain.test_case.schema import TestCaseCreateRequest

    payload = {
        "name": "login",
        "method": "GET",
        "path": "/api/users",
        "timeout_seconds": 30,
        "enabled": True,
    }
    payload.update(overrides)
    return TestCaseCreateRequest(**payload)


# === 1) Create + enabled round-trip ===


async def test_create_test_case_succeeds_and_assigns_id(service_db_session):
    from app.domain.test_case.service import TestCaseService

    owner = await _create_user_with_role(
        service_db_session, username="alice", email="alice@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    suite = await _create_suite(service_db_session, project=project)
    svc = TestCaseService(service_db_session)

    resp = await svc.create_test_case(
        suite.id, _make_create_request(name="login"), current_user=owner
    )

    assert resp.name == "login"
    assert resp.method == "GET"
    assert resp.path == "/api/users"
    assert resp.enabled is True
    assert resp.project_id == project.id
    assert resp.id is not None


async def test_create_test_case_disabled_round_trips(service_db_session):
    from app.domain.test_case.service import TestCaseService

    owner = await _create_user_with_role(
        service_db_session, username="alice1", email="alice1@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    suite = await _create_suite(service_db_session, project=project)
    svc = TestCaseService(service_db_session)

    resp = await svc.create_test_case(
        suite.id,
        _make_create_request(name="login", enabled=False),
        current_user=owner,
    )
    assert resp.enabled is False

    # Re-read from the DB to confirm the int column also flipped.
    from app.domain.test_case.repository import TestCaseRepository

    repo = TestCaseRepository(service_db_session)
    row = await repo.get_by_id(resp.id)
    assert row is not None
    assert row.status == 0


# === 2) Sort-order monotonic allocation ===


async def test_sort_order_grows_per_project(service_db_session):
    from app.domain.test_case.service import TestCaseService

    owner = await _create_user_with_role(
        service_db_session, username="alice2", email="alice2@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    suite = await _create_suite(service_db_session, project=project)
    svc = TestCaseService(service_db_session)

    a = await svc.create_test_case(
        suite.id, _make_create_request(name="a"), current_user=owner
    )
    b = await svc.create_test_case(
        suite.id, _make_create_request(name="b"), current_user=owner
    )
    c = await svc.create_test_case(
        suite.id, _make_create_request(name="c"), current_user=owner
    )

    assert (a.sort_order, b.sort_order, c.sort_order) == (0, 1, 2)

    listed = await svc.list_project_cases(project.id, current_user=owner)
    assert [item.name for item in listed.items] == ["a", "b", "c"]


async def test_sort_order_isolated_between_projects(service_db_session):
    from app.domain.test_case.service import TestCaseService

    owner = await _create_user_with_role(
        service_db_session, username="alice3", email="alice3@example.com"
    )
    p1 = await _create_project(service_db_session, owner=owner)
    p2 = await _create_project(service_db_session, owner=owner)
    suite1 = await _create_suite(service_db_session, project=p1, name="s1")
    suite2 = await _create_suite(service_db_session, project=p2, name="s2")
    svc = TestCaseService(service_db_session)

    a = await svc.create_test_case(
        suite1.id, _make_create_request(name="a"), current_user=owner
    )
    b = await svc.create_test_case(
        suite2.id, _make_create_request(name="b"), current_user=owner
    )

    # No cross-project leakage.
    assert a.sort_order == 0
    assert b.sort_order == 0


# === 3) Cross-user isolation on create / list / detail / update / delete ===


async def test_create_on_other_users_project_returns_403(service_db_session):
    from app.common.exceptions import ForbiddenException
    from app.domain.test_case.service import TestCaseService

    alice = await _create_user_with_role(
        service_db_session, username="alice4", email="alice4@example.com"
    )
    bob = await _create_user_with_role(
        service_db_session, username="bob4", email="bob4@example.com"
    )
    project = await _create_project(service_db_session, owner=alice)
    suite = await _create_suite(service_db_session, project=project)
    svc = TestCaseService(service_db_session)

    with pytest.raises(ForbiddenException):
        await svc.create_test_case(
            suite.id, _make_create_request(name="x"), current_user=bob
        )


async def test_create_on_missing_suite_returns_404(service_db_session):
    from app.common.exceptions import SuiteNotFoundException
    from app.domain.test_case.service import TestCaseService

    owner = await _create_user_with_role(
        service_db_session, username="ghost", email="ghost@example.com"
    )
    svc = TestCaseService(service_db_session)
    with pytest.raises(SuiteNotFoundException):
        await svc.create_test_case(
            uuid.uuid4(),
            _make_create_request(name="x"),
            current_user=owner,
        )


async def test_get_other_users_test_case_returns_403(service_db_session):
    from app.common.exceptions import ForbiddenException
    from app.domain.test_case.service import TestCaseService

    alice = await _create_user_with_role(
        service_db_session, username="alice5", email="alice5@example.com"
    )
    bob = await _create_user_with_role(
        service_db_session, username="bob5", email="bob5@example.com"
    )
    project = await _create_project(service_db_session, owner=alice)
    suite = await _create_suite(service_db_session, project=project)
    svc = TestCaseService(service_db_session)

    created = await svc.create_test_case(
        suite.id, _make_create_request(name="x"), current_user=alice
    )

    with pytest.raises(ForbiddenException):
        await svc.get_test_case(created.id, current_user=bob)


async def test_list_other_users_project_cases_returns_403(service_db_session):
    from app.common.exceptions import ForbiddenException
    from app.domain.test_case.service import TestCaseService

    alice = await _create_user_with_role(
        service_db_session, username="alice6", email="alice6@example.com"
    )
    bob = await _create_user_with_role(
        service_db_session, username="bob6", email="bob6@example.com"
    )
    project = await _create_project(service_db_session, owner=alice)
    svc = TestCaseService(service_db_session)
    with pytest.raises(ForbiddenException):
        await svc.list_project_cases(project.id, current_user=bob)


async def test_get_missing_test_case_returns_404(service_db_session):
    from app.common.exceptions import TestCaseNotFoundException
    from app.domain.test_case.service import TestCaseService

    owner = await _create_user_with_role(
        service_db_session, username="alice7", email="alice7@example.com"
    )
    svc = TestCaseService(service_db_session)
    with pytest.raises(TestCaseNotFoundException):
        await svc.get_test_case(uuid.uuid4(), current_user=owner)


# === 4) Partial update + delete cascade ===


async def test_partial_update_only_touches_supplied_fields(service_db_session):
    from app.domain.test_case.service import TestCaseService
    from app.domain.test_case.schema import TestCaseUpdateRequest

    owner = await _create_user_with_role(
        service_db_session, username="alice8", email="alice8@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    suite = await _create_suite(service_db_session, project=project)
    svc = TestCaseService(service_db_session)

    created = await svc.create_test_case(
        suite.id,
        _make_create_request(
            name="login", method="POST", path="/api/login", enabled=True
        ),
        current_user=owner,
    )

    updated = await svc.update_test_case(
        created.id,
        TestCaseUpdateRequest(path="/api/v2/login"),
        current_user=owner,
    )

    assert updated.path == "/api/v2/login"
    assert updated.method == "POST"  # unchanged
    assert updated.name == "login"  # unchanged
    assert updated.enabled is True  # unchanged


async def test_update_can_toggle_enabled(service_db_session):
    from app.domain.test_case.service import TestCaseService
    from app.domain.test_case.schema import TestCaseUpdateRequest

    owner = await _create_user_with_role(
        service_db_session, username="alice9", email="alice9@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    suite = await _create_suite(service_db_session, project=project)
    svc = TestCaseService(service_db_session)

    created = await svc.create_test_case(
        suite.id,
        _make_create_request(name="x", enabled=True),
        current_user=owner,
    )
    assert created.enabled is True

    updated = await svc.update_test_case(
        created.id,
        TestCaseUpdateRequest(enabled=False),
        current_user=owner,
    )
    assert updated.enabled is False


async def test_delete_cascades_to_suite_associations(service_db_session):
    """Deleting a test case must remove its ``api_suite_cases`` rows.

    Relies on ``PRAGMA foreign_keys=ON`` on the SQLite engine — see
    the ``service_db_engine`` fixture.
    """
    from sqlalchemy import select

    from app.domain.suite.model import ApiSuiteCase
    from app.domain.test_case.service import TestCaseService

    owner = await _create_user_with_role(
        service_db_session, username="alice10", email="alice10@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    suite = await _create_suite(service_db_session, project=project)
    svc = TestCaseService(service_db_session)

    created = await svc.create_test_case(
        suite.id, _make_create_request(name="x"), current_user=owner
    )

    rows = (
        await service_db_session.execute(
            select(ApiSuiteCase).where(
                ApiSuiteCase.test_case_id == created.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1

    await svc.delete_test_case(created.id, current_user=owner)

    after = (
        await service_db_session.execute(
            select(ApiSuiteCase).where(
                ApiSuiteCase.test_case_id == created.id
            )
        )
    ).scalars().all()
    assert after == []


async def test_delete_missing_test_case_returns_404(service_db_session):
    from app.common.exceptions import TestCaseNotFoundException
    from app.domain.test_case.service import TestCaseService

    owner = await _create_user_with_role(
        service_db_session, username="ghost2", email="ghost2@example.com"
    )
    svc = TestCaseService(service_db_session)
    with pytest.raises(TestCaseNotFoundException):
        await svc.delete_test_case(uuid.uuid4(), current_user=owner)


# === 5) Suite-scoped list excludes free-floating cases ===


async def test_list_suite_cases_excludes_floating_cases(service_db_session):
    from app.domain.test_case.service import TestCaseService

    owner = await _create_user_with_role(
        service_db_session, username="alice11", email="alice11@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    suite = await _create_suite(service_db_session, project=project)
    svc = TestCaseService(service_db_session)

    attached = await svc.create_test_case(
        suite.id, _make_create_request(name="attached"), current_user=owner
    )
    # Insert a free-floating case directly via the repository so it has
    # no row in ``api_suite_cases``.
    from app.domain.test_case.model import ApiTestCase
    from app.domain.test_case.repository import TestCaseRepository

    repo = TestCaseRepository(service_db_session)
    floating = ApiTestCase(
        id=uuid.uuid4(),
        project_id=project.id,
        name="floating",
        method="GET",
        path="/api/floating",
        body_type="none",
        timeout_seconds=30,
        status=1,
        sort_order=999,
    )
    await repo.create(floating)
    await service_db_session.commit()

    listed = await svc.list_suite_cases(suite.id, current_user=owner)
    assert [item.name for item in listed] == ["attached"]
    assert all(item.id != floating.id for item in listed)
    assert any(item.id == attached.id for item in listed)

    # The project list does include both.
    proj = await svc.list_project_cases(project.id, current_user=owner)
    assert {item.name for item in proj.items} == {"attached", "floating"}


# === 6) Search filter on project list ===


async def test_list_project_cases_search_filters_by_name(service_db_session):
    from app.domain.test_case.service import TestCaseService

    owner = await _create_user_with_role(
        service_db_session, username="alice12", email="alice12@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    suite = await _create_suite(service_db_session, project=project)
    svc = TestCaseService(service_db_session)

    for name in ("login", "logout", "register"):
        await svc.create_test_case(
            suite.id, _make_create_request(name=name), current_user=owner
        )

    listed = await svc.list_project_cases(
        project.id, current_user=owner, search="log"
    )
    assert sorted(c.name for c in listed.items) == ["login", "logout"]