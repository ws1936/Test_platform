"""Unit tests for :class:`EnvironmentService` (F005).

Focus is on the business rules that live in the service layer — the
HTTP layer is exercised separately by ``test_environment_router.py``.

Covered rules:

* Cross-project isolation: a user cannot reach environments of a
  project they don't own.
* ``(project_id, name)`` uniqueness — duplicates return 409.
* At most one default environment per project — promoting a second
  default demotes the first inside the same transaction.
* Default environments cannot be hard-deleted.
* ``set_default_environment`` demotes the previous default.
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

    The shared ``app`` / ``client`` fixtures in ``conftest.py`` only
    expose HTTP. For unit-level Service tests we drive the service
    through a real DB session instead of going through FastAPI.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

    from app.domain.environment.model import ApiEnvironment  # noqa: F401
    from app.domain.project.model import ApiProject  # noqa: F401
    from app.domain.role.model import Role  # noqa: F401
    from app.domain.user.model import User  # noqa: F401
    from app.infrastructure.database.session import Base

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


@pytest_asyncio.fixture
async def service_db_session(service_db_engine) -> AsyncGenerator:
    session_factory = async_sessionmaker(
        service_db_engine, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


# === Helpers (mirror conftest's user/role/project bootstrap) ===


async def _create_user_with_role(
    session,
    *,
    username: str,
    email: str,
    is_superuser: bool = False,
) -> "User":
    """Insert a fully-formed user (with role + hashed password).

    Mirrors what the auth registration flow ends up doing so the
    service layer can resolve ``current_user`` directly.
    """
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


def _make_environment_request(
    *,
    name: str = "dev",
    base_url: str = "https://api.dev.example.com",
    headers: dict | None = None,
    variables: dict | None = None,
    is_default: bool = False,
):
    """Build an ``EnvironmentCreateRequest`` directly (no HTTP)."""
    from app.domain.environment.schema import EnvironmentCreateRequest

    return EnvironmentCreateRequest(
        name=name,
        base_url=base_url,
        headers=headers,
        variables=variables,
        is_default=is_default,
    )


# === 1) Create + uniqueness ===


async def test_create_environment_succeeds_and_assigns_id(service_db_session):
    from app.domain.environment.service import EnvironmentService

    owner = await _create_user_with_role(
        service_db_session, username="alice", email="alice@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)

    svc = EnvironmentService(service_db_session)
    resp = await svc.create_environment(
        project.id,
        _make_environment_request(name="dev"),
        current_user=owner,
    )

    assert resp.name == "dev"
    assert resp.project_id == project.id
    assert resp.is_default is False
    assert resp.id is not None


async def test_create_environment_with_duplicate_name_raises_409(
    service_db_session,
):
    from app.common.exceptions import ConflictException
    from app.domain.environment.service import EnvironmentService

    owner = await _create_user_with_role(
        service_db_session, username="alice2", email="alice2@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = EnvironmentService(service_db_session)

    await svc.create_environment(
        project.id,
        _make_environment_request(name="dev"),
        current_user=owner,
    )

    with pytest.raises(ConflictException) as exc_info:
        await svc.create_environment(
            project.id,
            _make_environment_request(name="dev"),
            current_user=owner,
        )
    assert exc_info.value.status_code == 409


async def test_create_environment_on_other_users_project_returns_403(
    service_db_session,
):
    from app.common.exceptions import ForbiddenException
    from app.domain.environment.service import EnvironmentService

    alice = await _create_user_with_role(
        service_db_session, username="alice3", email="alice3@example.com"
    )
    bob = await _create_user_with_role(
        service_db_session, username="bob3", email="bob3@example.com"
    )
    alice_project = await _create_project(service_db_session, owner=alice)

    svc = EnvironmentService(service_db_session)
    with pytest.raises(ForbiddenException):
        await svc.create_environment(
            alice_project.id,
            _make_environment_request(name="dev"),
            current_user=bob,
        )


async def test_create_environment_on_missing_project_returns_404(
    service_db_session,
):
    from app.common.exceptions import ProjectNotFoundException
    from app.domain.environment.service import EnvironmentService

    owner = await _create_user_with_role(
        service_db_session, username="ghost", email="ghost@example.com"
    )
    svc = EnvironmentService(service_db_session)
    with pytest.raises(ProjectNotFoundException):
        await svc.create_environment(
            uuid.uuid4(),
            _make_environment_request(name="dev"),
            current_user=owner,
        )


# === 2) Default-environment mutual exclusion ===


async def test_promote_one_default_demotes_previous(service_db_session):
    from app.domain.environment.service import EnvironmentService

    owner = await _create_user_with_role(
        service_db_session, username="alice4", email="alice4@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = EnvironmentService(service_db_session)

    dev = await svc.create_environment(
        project.id,
        _make_environment_request(name="dev", is_default=True),
        current_user=owner,
    )
    staging = await svc.create_environment(
        project.id,
        _make_environment_request(name="staging", is_default=True),
        current_user=owner,
    )

    assert staging.is_default is True

    # Re-fetch dev from DB — must have been demoted.
    refreshed = await svc.repository.get_by_id(dev.id)
    assert refreshed is not None
    assert refreshed.is_default is False


async def test_set_default_promotes_and_demotes(service_db_session):
    from app.domain.environment.service import EnvironmentService

    owner = await _create_user_with_role(
        service_db_session, username="alice5", email="alice5@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = EnvironmentService(service_db_session)

    dev = await svc.create_environment(
        project.id,
        _make_environment_request(name="dev", is_default=True),
        current_user=owner,
    )
    staging = await svc.create_environment(
        project.id,
        _make_environment_request(name="staging"),
        current_user=owner,
    )

    resp = await svc.set_default_environment(staging.id, current_user=owner)
    assert resp.is_default is True

    dev_after = await svc.repository.get_by_id(dev.id)
    assert dev_after is not None
    assert dev_after.is_default is False


# === 3) Delete rules ===


async def test_delete_default_environment_raises_409(service_db_session):
    from app.common.exceptions import ConflictException
    from app.domain.environment.service import EnvironmentService

    owner = await _create_user_with_role(
        service_db_session, username="alice6", email="alice6@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = EnvironmentService(service_db_session)

    dev = await svc.create_environment(
        project.id,
        _make_environment_request(name="dev", is_default=True),
        current_user=owner,
    )

    with pytest.raises(ConflictException) as exc_info:
        await svc.delete_environment(dev.id, current_user=owner)
    assert exc_info.value.status_code == 409
    # Still present after the failed delete.
    refreshed = await svc.repository.get_by_id(dev.id)
    assert refreshed is not None


async def test_delete_non_default_environment_succeeds(service_db_session):
    from app.domain.environment.service import EnvironmentService

    owner = await _create_user_with_role(
        service_db_session, username="alice7", email="alice7@example.com"
    )
    project = await _create_project(service_db_session, owner=owner)
    svc = EnvironmentService(service_db_session)

    await svc.create_environment(
        project.id,
        _make_environment_request(name="dev", is_default=True),
        current_user=owner,
    )
    staging = await svc.create_environment(
        project.id,
        _make_environment_request(name="staging"),
        current_user=owner,
    )

    await svc.delete_environment(staging.id, current_user=owner)
    assert await svc.repository.get_by_id(staging.id) is None


async def test_delete_missing_environment_raises_404(service_db_session):
    from app.common.exceptions import EnvironmentNotFoundException
    from app.domain.environment.service import EnvironmentService

    owner = await _create_user_with_role(
        service_db_session, username="ghost7", email="ghost7@example.com"
    )
    svc = EnvironmentService(service_db_session)
    with pytest.raises(EnvironmentNotFoundException):
        await svc.delete_environment(uuid.uuid4(), current_user=owner)


# === 4) Cross-user isolation ===


async def test_get_other_users_environment_returns_403(service_db_session):
    from app.common.exceptions import ForbiddenException
    from app.domain.environment.service import EnvironmentService

    alice = await _create_user_with_role(
        service_db_session, username="alice8", email="alice8@example.com"
    )
    bob = await _create_user_with_role(
        service_db_session, username="bob8", email="bob8@example.com"
    )
    alice_project = await _create_project(service_db_session, owner=alice)
    svc = EnvironmentService(service_db_session)

    dev = await svc.create_environment(
        alice_project.id,
        _make_environment_request(name="dev"),
        current_user=alice,
    )

    with pytest.raises(ForbiddenException):
        await svc.get_environment(dev.id, current_user=bob)


async def test_list_other_users_project_environments_returns_403(
    service_db_session,
):
    from app.common.exceptions import ForbiddenException
    from app.domain.environment.schema import EnvironmentListQuery
    from app.domain.environment.service import EnvironmentService

    alice = await _create_user_with_role(
        service_db_session, username="alice9", email="alice9@example.com"
    )
    bob = await _create_user_with_role(
        service_db_session, username="bob9", email="bob9@example.com"
    )
    alice_project = await _create_project(service_db_session, owner=alice)
    svc = EnvironmentService(service_db_session)

    with pytest.raises(ForbiddenException):
        await svc.list_environments(
            alice_project.id,
            EnvironmentListQuery(),
            current_user=bob,
        )
