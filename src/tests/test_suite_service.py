"""Unit tests for :class:`SuiteService` (F006).

Focus is on the business rules that live in the service layer — the
HTTP layer is exercised separately by ``test_suite_router.py``.

Covered rules:

* Cross-project isolation: a user cannot reach suites of a project
  they don't own.
* ``(project_id, name)`` uniqueness — duplicates return 409.
* ``sort_order`` is monotonically allocated per project.
* ``bulk_add_cases`` is transactional + idempotent (re-adding the
  same ``test_case_id`` is a no-op reported in ``already_present``).
* Sort order is preserved in insertion order for the new entries.
* ``remove_case`` is idempotent (missing association is a no-op).
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


pytestmark = pytest.mark.asyncio


# === Fixtures local to this module ===


@pytest_asyncio.fixture
async def service_db_engine():
    """Standalone SQLite engine for direct Service-level tests.

    Mirrors ``test_environment_service.py``'s pattern so the service
    layer is exercised without going through the FastAPI app fixture.

    ``PRAGMA foreign_keys=ON`` is required because SQLite disables
    FK enforcement by default — without it, ``ON DELETE CASCADE``
    on ``api_suite_cases`` would silently no-op and break the
    "delete suite cascades to case rows" test.
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


async def _create_test_cases(session, *, project, case_ids: list[uuid.UUID]) -> None:
    """Seed persisted F007 identities required by F006 association tests."""
    from app.domain.test_case.model import ApiTestCase

    for index, case_id in enumerate(case_ids):
        session.add(
            ApiTestCase(
                id=case_id,
                project_id=project.id,
                name=f"case-{index}",
                method="GET",
                path=f"/case-{index}",
                body_type="none",
                timeout_seconds=30,
                status=1,
                sort_order=index,
            )
        )
    await session.commit()


def _make_suite_request(*, name: str, description: str | None = None):
    from app.domain.suite.schema import SuiteCreateRequest

    return SuiteCreateRequest(name=name, description=description)


def _make_bulk_request(*test_case_ids: uuid.UUID):
    from app.domain.suite.schema import SuiteCasesBulkCreate

    return SuiteCasesBulkCreate(test_case_ids=list(test_case_ids))


# === 1) Create + uniqueness ===


async def test_create_suite_succeeds_and_assigns_id(service_db_session):
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice", email="alice@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    resp = await svc.create_suite(
        project.id,
        _make_suite_request(name="smoke"),
        current_user=owner,
    )

    assert resp.name == "smoke"
    assert resp.project_id == project.id
    assert resp.sort_order == 0
    assert resp.id is not None


async def test_create_suite_with_duplicate_name_raises_409(service_db_session):
    from app.common.exceptions import ConflictException
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice2", email="alice2@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    await svc.create_suite(
        project.id, _make_suite_request(name="smoke"), current_user=owner
    )

    with pytest.raises(ConflictException) as exc_info:
        await svc.create_suite(
            project.id, _make_suite_request(name="smoke"), current_user=owner
        )
    assert exc_info.value.status_code == 409


async def test_create_suite_on_other_users_project_returns_403(service_db_session):
    from app.common.exceptions import ForbiddenException
    from app.domain.suite.service import SuiteService

    alice = await _create_user_with_role(
        service_db_session, username="alice3", email="alice3@example.com"
    )
    bob = await _create_user_with_role(
        service_db_session, username="bob3", email="bob3@example.com"
    )
    alice_project = await _create_project(service_db_session, owner=alice)

    svc = SuiteService(service_db_session)
    with pytest.raises(ForbiddenException):
        await svc.create_suite(
            alice_project.id,
            _make_suite_request(name="smoke"),
            current_user=bob,
        )


async def test_create_suite_on_missing_project_returns_404(service_db_session):
    from app.common.exceptions import ProjectNotFoundException
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="ghost", email="ghost@example.com"
    )
    svc = SuiteService(service_db_session)
    with pytest.raises(ProjectNotFoundException):
        await svc.create_suite(
            uuid.uuid4(),
            _make_suite_request(name="smoke"),
            current_user=owner,
        )


# === 2) sort_order monotonic allocation ===


async def test_sort_order_grows_per_project(service_db_session):
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice4", email="alice4@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    s1 = await svc.create_suite(
        project.id, _make_suite_request(name="a"), current_user=owner
    )
    s2 = await svc.create_suite(
        project.id, _make_suite_request(name="b"), current_user=owner
    )
    s3 = await svc.create_suite(
        project.id, _make_suite_request(name="c"), current_user=owner
    )

    assert (s1.sort_order, s2.sort_order, s3.sort_order) == (0, 1, 2)

    listed = await svc.list_suites(project.id, current_user=owner)
    assert [s.name for s in listed.items] == ["a", "b", "c"]


async def test_sort_order_isolated_between_projects(service_db_session):
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice5", email="alice5@example.com"
    )
    p1 = await _create_project(service_db_session, owner=owner)
    p2 = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    a = await svc.create_suite(
        p1.id, _make_suite_request(name="only-in-p1"), current_user=owner
    )
    b = await svc.create_suite(
        p2.id, _make_suite_request(name="only-in-p2"), current_user=owner
    )

    # Each project's first suite gets sort_order=0 — no cross-project leakage.
    assert a.sort_order == 0
    assert b.sort_order == 0


# === 3) Read / update / delete ===


async def test_get_suite_returns_403_for_non_owner(service_db_session):
    from app.common.exceptions import ForbiddenException
    from app.domain.suite.service import SuiteService

    alice = await _create_user_with_role(
        service_db_session, username="alice6", email="alice6@example.com"
    )
    bob = await _create_user_with_role(
        service_db_session, username="bob6", email="bob6@example.com"
    )
    project = await _create_project(service_db_session, owner=alice)
    svc = SuiteService(service_db_session)

    suite = await svc.create_suite(
        project.id, _make_suite_request(name="private"), current_user=alice
    )

    with pytest.raises(ForbiddenException):
        await svc.get_suite(suite.id, current_user=bob)


async def test_update_suite_with_duplicate_name_raises_409(service_db_session):
    from app.common.exceptions import ConflictException
    from app.domain.suite.service import SuiteService
    from app.domain.suite.schema import SuiteUpdateRequest

    owner = await _create_user_with_role(
        service_db_session, username="alice7", email="alice7@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    a = await svc.create_suite(
        project.id, _make_suite_request(name="a"), current_user=owner
    )
    b = await svc.create_suite(
        project.id, _make_suite_request(name="b"), current_user=owner
    )

    with pytest.raises(ConflictException):
        await svc.update_suite(
            b.id,
            SuiteUpdateRequest(name="a"),
            current_user=owner,
        )


async def test_delete_suite_removes_it(service_db_session):
    from app.domain.suite.service import SuiteService
    from app.common.exceptions import SuiteNotFoundException

    owner = await _create_user_with_role(
        service_db_session, username="alice8", email="alice8@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    suite = await svc.create_suite(
        project.id, _make_suite_request(name="x"), current_user=owner
    )
    await svc.delete_suite(suite.id, current_user=owner)

    with pytest.raises(SuiteNotFoundException):
        await svc.get_suite(suite.id, current_user=owner)


# === 4) SuiteCase bulk add — idempotency + ordering ===


async def test_bulk_add_cases_appends_in_caller_order(service_db_session):
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice9", email="alice9@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    suite = await svc.create_suite(
        project.id, _make_suite_request(name="s"), current_user=owner
    )

    tc_a, tc_b, tc_c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await _create_test_cases(
        service_db_session, project=project, case_ids=[tc_a, tc_b, tc_c]
    )
    resp = await svc.bulk_add_cases(
        suite.id,
        _make_bulk_request(tc_a, tc_b, tc_c),
        current_user=owner,
    )

    assert [str(a.test_case_id) for a in resp.added] == [
        str(tc_a),
        str(tc_b),
        str(tc_c),
    ]
    assert resp.already_present == []
    assert [a.sort_order for a in resp.added] == [0, 1, 2]


async def test_bulk_add_cases_is_idempotent(service_db_session):
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice10", email="alice10@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    suite = await svc.create_suite(
        project.id, _make_suite_request(name="s"), current_user=owner
    )
    tc_a, tc_b = uuid.uuid4(), uuid.uuid4()
    await _create_test_cases(service_db_session, project=project, case_ids=[tc_a, tc_b])

    first = await svc.bulk_add_cases(
        suite.id,
        _make_bulk_request(tc_a, tc_b),
        current_user=owner,
    )
    assert len(first.added) == 2
    assert first.already_present == []

    # Re-add the same two — should be a no-op.
    second = await svc.bulk_add_cases(
        suite.id,
        _make_bulk_request(tc_a, tc_b),
        current_user=owner,
    )
    assert second.added == []
    assert [str(x) for x in second.already_present] == [str(tc_a), str(tc_b)]


async def test_bulk_add_deduplicates_caller_input(service_db_session):
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice11", email="alice11@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    suite = await svc.create_suite(
        project.id, _make_suite_request(name="s"), current_user=owner
    )

    tc = uuid.uuid4()
    await _create_test_cases(service_db_session, project=project, case_ids=[tc])
    resp = await svc.bulk_add_cases(
        suite.id,
        _make_bulk_request(tc, tc, tc),
        current_user=owner,
    )
    assert len(resp.added) == 1
    assert [a.test_case_id for a in resp.added] == [tc]


async def test_bulk_add_mixed_new_and_existing(service_db_session):
    """Half of the inputs are new, half are already present — both are reported."""
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice12", email="alice12@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    suite = await svc.create_suite(
        project.id, _make_suite_request(name="s"), current_user=owner
    )

    old = uuid.uuid4()
    new = uuid.uuid4()
    await _create_test_cases(service_db_session, project=project, case_ids=[old, new])
    # Seed with `old`.
    await svc.bulk_add_cases(suite.id, _make_bulk_request(old), current_user=owner)

    # Now mix: old + new + old (duplicates within caller input).
    resp = await svc.bulk_add_cases(
        suite.id,
        _make_bulk_request(old, new, old),
        current_user=owner,
    )
    assert len(resp.added) == 1
    assert resp.added[0].test_case_id == new
    # ``already_present`` is reported once per distinct pre-existing ID.
    assert [str(x) for x in resp.already_present] == [str(old)]


async def test_list_suite_cases_returns_insertion_order(service_db_session):
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice13", email="alice13@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    suite = await svc.create_suite(
        project.id, _make_suite_request(name="s"), current_user=owner
    )
    ids = [uuid.uuid4() for _ in range(3)]
    await _create_test_cases(service_db_session, project=project, case_ids=ids)
    await svc.bulk_add_cases(suite.id, _make_bulk_request(*ids), current_user=owner)

    rows = await svc.list_suite_cases(suite.id, current_user=owner)
    assert [str(r.test_case_id) for r in rows] == [str(i) for i in ids]
    assert [r.sort_order for r in rows] == [0, 1, 2]


async def test_remove_case_is_idempotent(service_db_session):
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice14", email="alice14@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    suite = await svc.create_suite(
        project.id, _make_suite_request(name="s"), current_user=owner
    )
    tc = uuid.uuid4()
    await _create_test_cases(service_db_session, project=project, case_ids=[tc])
    await svc.bulk_add_cases(suite.id, _make_bulk_request(tc), current_user=owner)

    # First remove: deletes the row.
    await svc.remove_case(suite.id, tc, current_user=owner)
    rows = await svc.list_suite_cases(suite.id, current_user=owner)
    assert rows == []

    # Second remove: no-op, must not raise.
    await svc.remove_case(suite.id, tc, current_user=owner)


async def test_delete_suite_cascades_to_case_rows(service_db_session):
    from app.domain.suite.service import SuiteService

    owner = await _create_user_with_role(
        service_db_session, username="alice15", email="alice15@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = SuiteService(service_db_session)

    suite = await svc.create_suite(
        project.id, _make_suite_request(name="s"), current_user=owner
    )
    case_ids = [uuid.uuid4(), uuid.uuid4()]
    await _create_test_cases(service_db_session, project=project, case_ids=case_ids)
    await svc.bulk_add_cases(
        suite.id, _make_bulk_request(*case_ids), current_user=owner
    )
    assert len(await svc.list_suite_cases(suite.id, current_user=owner)) == 2

    await svc.delete_suite(suite.id, current_user=owner)

    # The FK CASCADE should have wiped the associations even though
    # we deleted via the suite row (not the case rows).
    remaining = await svc.repository.list_cases_by_suite(suite.id)
    assert remaining == []


# === 5) Cross-user isolation on case operations ===


async def test_non_owner_cannot_bulk_add_cases(service_db_session):
    from app.common.exceptions import ForbiddenException
    from app.domain.suite.service import SuiteService

    alice = await _create_user_with_role(
        service_db_session, username="alice16", email="alice16@example.com"
    )
    bob = await _create_user_with_role(
        service_db_session, username="bob16", email="bob16@example.com"
    )
    project = await _create_project(service_db_session, owner=alice)
    svc = SuiteService(service_db_session)

    suite = await svc.create_suite(
        project.id, _make_suite_request(name="s"), current_user=alice
    )

    with pytest.raises(ForbiddenException):
        await svc.bulk_add_cases(
            suite.id,
            _make_bulk_request(uuid.uuid4()),
            current_user=bob,
        )
