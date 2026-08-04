"""F014 有限并发执行 — Router/Service 层 ``concurrency`` 参数透传测试。

覆盖 ``POST /projects/{pid}/runs?concurrency=N`` 和
``POST /test-cases/{cid}/run?concurrency=N`` 两条触发执行入口：

* 不传 → :class:`TestRunner` 收到 ``max_concurrency=None``（走 settings 默认）。
* 显式 ``concurrency=N`` → :class:`TestRunner` 收到 ``max_concurrency=N``。
* ``concurrency=0`` / ``concurrency=200`` → Router 层 422，不进 Service。
* ``run_single_case`` 入口对称。

策略：monkeypatch :class:`TestRunner`（service 层实际 import 的那个），
捕获 ``__init__`` 的 ``max_concurrency`` 入参；构造一个 noop 的
``execute_run``，让 Service 不必真的去跑 case。
"""
from __future__ import annotations

import uuid
from typing import Any, List, Optional

import pytest

from app.common.security import hash_password
from app.config import settings
from app.domain.environment.model import ApiEnvironment
from app.domain.environment.repository import EnvironmentRepository
from app.domain.project.model import ApiProject
from app.domain.role.model import Role
from app.domain.test_case.model import ApiTestCase
from app.domain.test_engine.runner import TestRunner
from app.domain.test_run.model import ApiTestRun
from app.domain.user.model import User
from app.domain.user.repository import UserRepository


# ---------------------------------------------------------------------------
# Fixtures (mirror the patterns used by test_test_run_router.py)
# ---------------------------------------------------------------------------


async def _create_user_with_role(db_session, *, username: str, email: str) -> User:
    role = Role(
        id=uuid.uuid4(),
        name=f"role_{uuid.uuid4().hex[:8]}",
        description="f014 router test role",
        permissions=None,
        is_system=False,
    )
    db_session.add(role)
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        username=username,
        email=email,
        hashed_password=hash_password("TestPass123!"),
        nickname=username.capitalize(),
        phone="13800000000",
        status=1,
        role_id=role.id,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _create_project(db_session, *, owner: User) -> ApiProject:
    project = ApiProject(
        id=uuid.uuid4(),
        name=f"p-{uuid.uuid4().hex[:8]}",
        description="f014 router test",
        owner_id=owner.id,
    )
    db_session.add(project)
    await db_session.commit()
    return project


async def _create_environment(db_session, *, project: ApiProject) -> ApiEnvironment:
    env = ApiEnvironment(
        id=uuid.uuid4(),
        project_id=project.id,
        name="dev",
        base_url="https://api.test",
        headers={},
        variables={},
        is_default=True,
    )
    db_session.add(env)
    await db_session.commit()
    return env


async def _create_case(db_session, *, project: ApiProject) -> ApiTestCase:
    case = ApiTestCase(
        id=uuid.uuid4(),
        project_id=project.id,
        name="c1",
        method="GET",
        path="/api/f014",
        headers={},
        query_params={},
        body_type="none",
        body=None,
        assertions=[],
        timeout_seconds=10,
        status=1,
        sort_order=0,
    )
    db_session.add(case)
    await db_session.commit()
    return case


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, *, username: str, email: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "TestPass123!",
            "nickname": username.capitalize(),
            "phone": "13800000000",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {"id": body["user"]["id"], "token": body["token"]["access_token"]}


# ---------------------------------------------------------------------------
# TestRunner spy
# ---------------------------------------------------------------------------


class _RunnerSpy:
    """Captures every :class:`TestRunner.__init__` call and short-circuits execution.

    The Service layer constructs ``TestRunner(self.session, max_concurrency=...)``
    then calls ``execute_run(...)``. We replace the entire class so:

    * ``__init__`` records ``session`` and ``max_concurrency`` plus any kwargs.
    * ``execute_run`` returns a no-op finished ``ApiTestRun`` so the
      Service can decorate + return a response without real I/O.
    """

    instances: List["_RunnerSpy"] = []

    def __init__(self, session: Any, *, executor: Any = None,
                 max_concurrency: Optional[int] = None) -> None:
        self.session = session
        self.executor = executor
        self.max_concurrency = max_concurrency
        _RunnerSpy.instances.append(self)

    async def execute_run(self, *, run: ApiTestRun, env: Any,
                          case_ids: Any) -> ApiTestRun:
        # Mark the run as finished so the Service path doesn't blow up
        # trying to read a half-written run.
        run.status = "finished"
        run.passed = len(case_ids)
        run.failed = 0
        run.error = 0
        run.skipped = 0
        return run

    async def aclose(self) -> None:  # pragma: no cover - safety
        return None


def _patch_test_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``TestRunner`` in the service module's namespace."""
    from app.domain.test_run import service as service_module

    monkeypatch.setattr(service_module, "TestRunner", _RunnerSpy)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_create_run_omits_concurrency_uses_default(client, db_session, monkeypatch):
    """No ``?concurrency=`` → TestRunner receives ``max_concurrency=None``.

    The runner itself falls back to ``settings.TEST_RUN_MAX_CONCURRENCY``
    when the value is ``None``; this test only asserts the Service
    correctly forwards the unset state.
    """
    _RunnerSpy.instances.clear()
    _patch_test_runner(monkeypatch)

    alice = await _register(client, username="f014router1", email="f014router1@example.com")
    user_repo = UserRepository(db_session)
    owner = await user_repo.get_by_id(uuid.UUID(alice["id"]))
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)
    await _create_case(db_session, project=project)

    resp = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "name": "default-concurrency",
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(alice["token"]),
    )
    assert resp.status_code == 201, resp.text

    assert len(_RunnerSpy.instances) == 1
    spy = _RunnerSpy.instances[0]
    # Service must not invent a number — let the runner apply the default.
    assert spy.max_concurrency is None
    # Sanity: the documented default lives in settings.
    assert settings.TEST_RUN_MAX_CONCURRENCY >= 1


@pytest.mark.parametrize("value", [1, 2, 4, 8, 64])
async def test_create_run_with_concurrency_forwarded(client, db_session, monkeypatch, value):
    """``?concurrency=N`` → Service forwards ``max_concurrency=N`` to runner."""
    _RunnerSpy.instances.clear()
    _patch_test_runner(monkeypatch)

    suffix = f"f014r2_{value}_{uuid.uuid4().hex[:6]}"
    user = await _register(client, username=suffix, email=f"{suffix}@example.com")
    user_repo = UserRepository(db_session)
    owner = await user_repo.get_by_id(uuid.UUID(user["id"]))
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)
    await _create_case(db_session, project=project)

    resp = await client.post(
        f"/api/v1/projects/{project.id}/runs?concurrency={value}",
        json={
            "name": f"concurrency-{value}",
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 201, resp.text

    assert len(_RunnerSpy.instances) == 1
    assert _RunnerSpy.instances[0].max_concurrency == value


async def test_create_run_with_concurrency_zero_returns_422(client, db_session):
    """``?concurrency=0`` violates ``ge=1`` → FastAPI 422, runner never invoked."""
    suffix = f"f014r3_{uuid.uuid4().hex[:6]}"
    user = await _register(client, username=suffix, email=f"{suffix}@example.com")
    user_repo = UserRepository(db_session)
    owner = await user_repo.get_by_id(uuid.UUID(user["id"]))
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)

    resp = await client.post(
        f"/api/v1/projects/{project.id}/runs?concurrency=0",
        json={
            "name": "bad-concurrency",
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422
    # No need to assert spy wasn't called; FastAPI short-circuits before
    # the Service dependency is resolved.


async def test_create_run_with_concurrency_too_large_returns_422(client, db_session):
    """``?concurrency=200`` violates ``le=64`` → FastAPI 422."""
    suffix = f"f014r4_{uuid.uuid4().hex[:6]}"
    user = await _register(client, username=suffix, email=f"{suffix}@example.com")
    user_repo = UserRepository(db_session)
    owner = await user_repo.get_by_id(uuid.UUID(user["id"]))
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)

    resp = await client.post(
        f"/api/v1/projects/{project.id}/runs?concurrency=200",
        json={
            "name": "too-large",
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 422


async def test_run_single_case_with_concurrency_forwarded(client, db_session, monkeypatch):
    """``POST /test-cases/{cid}/run?concurrency=N`` → forwarded to runner."""
    _RunnerSpy.instances.clear()
    _patch_test_runner(monkeypatch)

    suffix = f"f014r5_{uuid.uuid4().hex[:6]}"
    user = await _register(client, username=suffix, email=f"{suffix}@example.com")
    user_repo = UserRepository(db_session)
    owner = await user_repo.get_by_id(uuid.UUID(user["id"]))
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)
    case = await _create_case(db_session, project=project)

    resp = await client.post(
        f"/api/v1/test-cases/{case.id}/run"
        f"?environment_id={env.id}&concurrency=4",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 201, resp.text

    assert len(_RunnerSpy.instances) == 1
    # Even though 1 case has nothing to overlap, the value is forwarded
    # for symmetry with the multi-case endpoint.
    assert _RunnerSpy.instances[0].max_concurrency == 4
