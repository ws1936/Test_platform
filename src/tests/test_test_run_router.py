"""HTTP API tests for F010 test run management router.

Covers all 6 endpoints defined in API_GUIDE §3.7 + §3.8:

* ``POST   /projects/{project_id}/runs``              — create + execute
* ``GET    /projects/{project_id}/runs``              — list project runs
* ``GET    /runs/{run_id}``                           — run detail
* ``GET    /runs/{run_id}/results``                   — list results
* ``GET    /results/{result_id}``                     — single result
* ``POST   /test-cases/{case_id}/run``                — single-case run

Strategy
--------
We mock :class:`ApiExecutor` so the tests don't hit the network and
so every response is deterministic. The fixtures create a real
project + environment in the SQLite test DB, then trigger runs that
record ``status="passed"`` or ``status="failed"`` deterministically.

The goal of these tests is to exercise the **router → service →
runner → DB** plumbing, not the engine internals (those live in
``test_executor.py`` / ``test_request_builder.py``).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Mapping, Optional

import pytest

from app.common.security import hash_password
from app.domain.environment.model import ApiEnvironment
from app.domain.environment.repository import EnvironmentRepository
from app.domain.project.model import ApiProject
from app.domain.project.repository import ProjectRepository
from app.domain.role.model import Role
from app.domain.suite.model import ApiSuiteCase
from app.domain.suite.repository import SuiteRepository
from app.domain.test_case.model import ApiTestCase
from app.domain.test_case.repository import TestCaseRepository
from app.domain.test_engine.runner import TestRunner
from app.domain.user.model import User
from app.domain.user.repository import UserRepository


pytestmark = pytest.mark.asyncio


# === Test helpers ===========================================================


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@dataclass
class _FakeResponse:
    """Minimal httpx.Response stand-in (only the attributes the runner reads)."""

    status_code: int = 200
    text: str = ""
    _json: Any = None
    elapsed: timedelta = field(default_factory=lambda: timedelta(milliseconds=42))
    headers: Mapping[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        return json.loads(self.text)


class _ScriptedExecutor:
    """Drop-in replacement for :class:`ApiExecutor` driven by a queue of responses.

    Each call to ``execute`` pops the next ``response`` from the
    queue; when the queue is empty we fall back to a default 200 OK
    with a small JSON body. If ``raise_*`` is set on a queued entry
    the executor raises the matching engine exception instead of
    returning the response.
    """

    def __init__(self) -> None:
        self.queue: list[dict[str, Any]] = []
        self.calls: list[Any] = []

    def push(self, *, status_code: int = 200, body: Any = None, headers: Optional[dict] = None,
             text: Optional[str] = None,
             raise_timeout: bool = False,
             raise_connection: bool = False,
             raise_generic: bool = False) -> None:
        self.queue.append(
            {
                "status_code": status_code,
                "body": body,
                "text": text,
                "headers": headers or {},
                "raise_timeout": raise_timeout,
                "raise_connection": raise_connection,
                "raise_generic": raise_generic,
            }
        )

    async def execute(self, request):
        from app.domain.test_engine.exceptions import (
            ApiConnectionError,
            ApiExecutionError,
            ApiExecutionTimeoutError,
        )

        self.calls.append(request)
        entry = self.queue.pop(0) if self.queue else {
            "status_code": 200,
            "body": {"ok": True},
            "headers": {},
            "text": None,
            "raise_timeout": False,
            "raise_connection": False,
            "raise_generic": False,
        }
        if entry["raise_timeout"]:
            raise ApiExecutionTimeoutError(
                f"request to {request.url} timed out"
            )
        if entry["raise_connection"]:
            raise ApiConnectionError(
                f"could not connect to {request.url}"
            )
        if entry["raise_generic"]:
            raise ApiExecutionError(
                f"HTTP error for {request.method} {request.url}"
            )
        # ``json=`` is consumed by the F009 ``response.json()`` helper
        # but our dataclass field is named ``_json`` to avoid the
        # shadowing; pass via ``_json=`` instead.
        return _FakeResponse(
            status_code=entry["status_code"],
            _json=entry["body"],
            text=entry["text"] or "",
            headers=entry["headers"],
        )


async def _create_user_with_role(db_session, *, username: str, email: str,
                                  is_superuser: bool = False) -> User:
    """Insert a fully-formed user with a role; mirrors the F001 fixture pattern."""
    role = Role(
        id=uuid.uuid4(),
        name=f"role_{uuid.uuid4().hex[:8]}",
        description="test role",
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
        is_superuser=is_superuser,
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _create_project(db_session, *, owner: User, name: str = "P") -> ApiProject:
    project = ApiProject(
        id=uuid.uuid4(),
        name=name,
        description="run router test",
        owner_id=owner.id,
    )
    db_session.add(project)
    await db_session.commit()
    return project


async def _create_environment(
    db_session, *, project: ApiProject, name: str = "dev",
    base_url: str = "https://api.test",
) -> ApiEnvironment:
    env = ApiEnvironment(
        id=uuid.uuid4(),
        project_id=project.id,
        name=name,
        base_url=base_url,
        headers={},
        variables={},
        is_default=True,
    )
    db_session.add(env)
    await db_session.commit()
    return env


async def _create_case(
    db_session, *, project: ApiProject, name: str = "case-1",
    method: str = "GET", path: str = "/api/users",
    assertions: Optional[list[dict[str, Any]]] = None,
    enabled: bool = True,
) -> ApiTestCase:
    case = ApiTestCase(
        id=uuid.uuid4(),
        project_id=project.id,
        name=name,
        method=method,
        path=path,
        headers={},
        query_params={},
        body_type="none",
        body=None,
        assertions=assertions,
        timeout_seconds=10,
        status=1 if enabled else 0,
        sort_order=0,
    )
    db_session.add(case)
    await db_session.commit()
    return case


async def _register(client, *, username: str, email: str,
                   admin_token: Optional[str] = None) -> dict:
    """Register a fresh user via the public auth route."""
    headers = _auth(admin_token) if admin_token else None
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "TestPass123!",
            "nickname": username.capitalize(),
            "phone": "13800000000",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {"id": body["user"]["id"], "token": body["token"]["access_token"]}


def _patch_runner_executor(monkeypatch, executor: _ScriptedExecutor):
    """Replace :class:`ApiExecutor` inside ``runner.py`` with a scripted shim.

    ``TestRunner.__init__`` constructs an ``ApiExecutor()`` when no
    executor is passed in, but that ``ApiExecutor`` class was
    imported at module load time — monkeypatching the source module
    after the fact does not affect the runner's reference. Patching
    ``app.domain.test_engine.runner.ApiExecutor`` directly replaces
    the binding the runner actually uses.
    """
    from app.domain.test_engine import runner as runner_module

    class _ExecutorFactory:
        """Stand-in for ``ApiExecutor`` whose ``execute`` reads from
        our scripted queue."""

        def __init__(self, *args, **kwargs):
            self._executor = executor

        async def execute(self, request):
            return await self._executor.execute(request)

        async def aclose(self):
            return None

    # Patch the binding the runner module sees.
    monkeypatch.setattr(runner_module, "ApiExecutor", _ExecutorFactory)
    # Also patch the source module so any future ``from ... import
    # ApiExecutor`` inside the test session picks up the shim.
    from app.domain.test_engine import executor as executor_module

    monkeypatch.setattr(executor_module, "ApiExecutor", _ExecutorFactory)


# === 1. POST /projects/{project_id}/runs ====================================


async def test_create_project_run_passes(client, db_session):
    """Project scope: every enabled case in the project is executed."""
    owner = await _register(client, username="alice", email="alice@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    case = await _create_case(
        db_session, project=project, name="c1", path="/api/x"
    )

    # Inject a scripted executor.
    scripted = _ScriptedExecutor()
    scripted.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), scripted)

    resp = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "name": "smoke",
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(owner["token"]),
    )
    # Don't gate the whole test on the monkeypatch plumbing; print
    # the body to help diagnose if it fails.
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["scope"] == "project"
    assert body["status"] == "finished"
    assert body["total"] == 1
    assert body["passed"] == 1
    assert body["failed"] == 0


async def test_create_project_run_fails_when_assertion_fails(client, db_session):
    owner = await _register(client, username="bob", email="bob@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    # 500 from upstream → assertion expects 200 → fails.
    case = await _create_case(
        db_session,
        project=project,
        name="c1",
        assertions=[
            {"type": "status_code", "operator": "eq", "expected": 200},
        ],
    )

    scripted = _ScriptedExecutor()
    scripted.push(status_code=500)
    _patch_runner_executor(pytest.MonkeyPatch(), scripted)

    resp = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["failed"] == 1
    assert body["passed"] == 0


async def test_create_project_run_with_invalid_environment_returns_404(
    client, db_session
):
    owner = await _register(client, username="carol", email="carol@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)

    resp = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "environment_id": str(uuid.uuid4()),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "ENVIRONMENT_NOT_FOUND"


async def test_create_run_requires_owner(client, db_session):
    alice = await _register(client, username="dan", email="dan@example.com")
    bob = await _register(
        client, username="eve", email="eve@example.com",
        admin_token=alice["token"],
    )
    user_repo = UserRepository(db_session)
    alice_user = await user_repo.get_by_id(uuid.UUID(alice["id"]))
    project = await _create_project(db_session, owner=alice_user)
    env = await _create_environment(db_session, project=project)

    resp = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


async def test_create_run_without_token_returns_401(client, db_session):
    alice = await _register(client, username="frank", email="frank@example.com")
    user_repo = UserRepository(db_session)
    alice_user = await user_repo.get_by_id(uuid.UUID(alice["id"]))
    project = await _create_project(db_session, owner=alice_user)
    resp = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "environment_id": str(uuid.uuid4()),
            "scope": "project",
            "scope_id": str(project.id),
        },
    )
    assert resp.status_code == 401


async def test_create_run_with_invalid_scope_returns_422(client, db_session):
    owner = await _register(client, username="grace", email="grace@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    resp = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "environment_id": str(env.id),
            "scope": "bogus",
            "scope_id": str(project.id),
        },
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 422


# === 2. GET /projects/{project_id}/runs ====================================


async def test_list_project_runs_returns_newest_first(client, db_session):
    owner = await _register(client, username="henry", email="henry@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    # The project needs at least one enabled case so the run can
    # actually execute (scope=project rejects empty projects with 400).
    await _create_case(db_session, project=project, name="c1")

    scripted = _ScriptedExecutor()
    for _ in range(2):
        scripted.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), scripted)

    # Run twice.
    for _ in range(2):
        r = await client.post(
            f"/api/v1/projects/{project.id}/runs",
            json={
                "environment_id": str(env.id),
                "scope": "project",
                "scope_id": str(project.id),
            },
            headers=_auth(owner["token"]),
        )
        assert r.status_code == 201, r.text

    resp = await client.get(
        f"/api/v1/projects/{project.id}/runs",
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


async def test_list_runs_on_other_users_project_returns_403(client, db_session):
    alice = await _register(client, username="ivy", email="ivy@example.com")
    bob = await _register(
        client, username="jack", email="jack@example.com",
        admin_token=alice["token"],
    )
    user_repo = UserRepository(db_session)
    alice_user = await user_repo.get_by_id(uuid.UUID(alice["id"]))
    project = await _create_project(db_session, owner=alice_user)

    resp = await client.get(
        f"/api/v1/projects/{project.id}/runs",
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403


# === 3. GET /runs/{run_id} ================================================


async def test_get_run_returns_201_run_with_counters(client, db_session):
    owner = await _register(client, username="kate", email="kate@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    await _create_case(db_session, project=project, name="c1")

    scripted = _ScriptedExecutor()
    scripted.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), scripted)

    create = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(owner["token"]),
    )
    rid = create.json()["id"]

    resp = await client.get(
        f"/api/v1/runs/{rid}", headers=_auth(owner["token"])
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == rid
    assert body["status"] == "finished"
    assert body["total"] == 1
    assert body["passed"] == 1


async def test_get_nonexistent_run_returns_404(client):
    user = await _register(client, username="liam", email="liam@example.com")
    resp = await client.get(
        f"/api/v1/runs/{uuid.uuid4()}",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "TEST_RUN_NOT_FOUND"


# === 4. GET /runs/{run_id}/results ========================================


async def test_list_run_results_returns_one_per_case(client, db_session):
    owner = await _register(client, username="mia", email="mia@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    # Two cases → two results.
    await _create_case(db_session, project=project, name="c1", path="/api/a")
    await _create_case(db_session, project=project, name="c2", path="/api/b")

    scripted = _ScriptedExecutor()
    scripted.push(status_code=200, body={"ok": True})
    scripted.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), scripted)

    create = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(owner["token"]),
    )
    rid = create.json()["id"]

    resp = await client.get(
        f"/api/v1/runs/{rid}/results", headers=_auth(owner["token"])
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    # Every result has a status + snapshot.
    for r in body["items"]:
        assert r["status"] in {"passed", "failed", "error", "skipped"}
        assert "case_name" in r
        assert "request_snapshot" in r
        assert "response_snapshot" in r
        assert "assertions_snapshot" in r


# === 5. GET /results/{result_id} ==========================================


async def test_get_single_result_returns_full_payload(client, db_session):
    owner = await _register(client, username="nina", email="nina@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    await _create_case(
        db_session,
        project=project,
        assertions=[
            {"type": "status_code", "operator": "eq", "expected": 200},
        ],
    )

    scripted = _ScriptedExecutor()
    scripted.push(status_code=200, body={"id": 1})
    _patch_runner_executor(pytest.MonkeyPatch(), scripted)

    create = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(owner["token"]),
    )
    rid = create.json()["id"]
    listing = await client.get(
        f"/api/v1/runs/{rid}/results", headers=_auth(owner["token"])
    )
    result_id = listing.json()["items"][0]["id"]

    resp = await client.get(
        f"/api/v1/results/{result_id}", headers=_auth(owner["token"])
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == result_id
    # Snapshot integrity.
    assert body["status"] == "passed"
    assert body["request_snapshot"]["method"] == "GET"
    assert body["response_snapshot"]["status_code"] == 200


async def test_get_nonexistent_result_returns_404(client):
    user = await _register(client, username="oscar", email="oscar@example.com")
    resp = await client.get(
        f"/api/v1/results/{uuid.uuid4()}",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "TEST_RESULT_NOT_FOUND"


# === 6. POST /test-cases/{case_id}/run =====================================


async def test_run_single_case_endpoint(client, db_session):
    owner = await _register(client, username="paul", email="paul@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    case = await _create_case(
        db_session, project=project, name="single", path="/api/x"
    )

    scripted = _ScriptedExecutor()
    scripted.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), scripted)

    resp = await client.post(
        f"/api/v1/test-cases/{case.id}/run",
        params={"environment_id": str(env.id)},
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["scope"] == "case"
    assert body["total"] == 1
    assert body["passed"] == 1


async def test_run_single_case_with_missing_environment_returns_404(
    client, db_session
):
    owner = await _register(client, username="quinn", email="quinn@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    case = await _create_case(db_session, project=project)

    resp = await client.post(
        f"/api/v1/test-cases/{case.id}/run",
        params={"environment_id": str(uuid.uuid4())},
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "ENVIRONMENT_NOT_FOUND"


async def test_run_disabled_case_returns_400(client, db_session):
    owner = await _register(client, username="rachel", email="rachel@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    case = await _create_case(db_session, project=project, enabled=False)

    resp = await client.post(
        f"/api/v1/test-cases/{case.id}/run",
        params={"environment_id": str(env.id)},
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 400
    assert "disabled" in resp.json()["message"].lower()


# === 7. End-to-end error mapping (32001 / 32002 / 32003) ==============


async def test_timeout_results_in_error_result_row(client, db_session):
    """httpx.TimeoutException → result.status='error' / error_code='API_EXECUTION_TIMEOUT'."""
    owner = await _register(client, username="sam", email="sam@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    await _create_case(db_session, project=project, name="slow")

    scripted = _ScriptedExecutor()
    scripted.push(raise_timeout=True)
    _patch_runner_executor(pytest.MonkeyPatch(), scripted)

    create = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(owner["token"]),
    )
    assert create.status_code == 201
    body = create.json()
    assert body["error"] == 1
    assert body["passed"] == 0

    listing = await client.get(
        f"/api/v1/runs/{body['id']}/results", headers=_auth(owner["token"])
    )
    item = listing.json()["items"][0]
    assert item["status"] == "error"
    assert item["error_code"] == "API_EXECUTION_TIMEOUT"


async def test_connection_error_results_in_error_result_row(client, db_session):
    owner = await _register(client, username="tina", email="tina@example.com")
    user_repo = UserRepository(db_session)
    owner_user = await user_repo.get_by_id(uuid.UUID(owner["id"]))
    project = await _create_project(db_session, owner=owner_user)
    env = await _create_environment(db_session, project=project)
    await _create_case(db_session, project=project, name="unreachable")

    scripted = _ScriptedExecutor()
    scripted.push(raise_connection=True)
    _patch_runner_executor(pytest.MonkeyPatch(), scripted)

    create = await client.post(
        f"/api/v1/projects/{project.id}/runs",
        json={
            "environment_id": str(env.id),
            "scope": "project",
            "scope_id": str(project.id),
        },
        headers=_auth(owner["token"]),
    )
    body = create.json()
    assert body["error"] == 1
    listing = await client.get(
        f"/api/v1/runs/{body['id']}/results", headers=_auth(owner["token"])
    )
    item = listing.json()["items"][0]
    assert item["error_code"] == "API_CONNECTION_ERROR"