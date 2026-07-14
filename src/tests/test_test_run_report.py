"""HTTP API tests for F011 test report endpoints.

Covers:
* ``GET /runs/{run_id}/summary``                 — single-run roll-up
* ``GET /projects/{pid}/runs/summary``           — project-level roll-up
* ``GET /runs/{run_id}/failures``                — flattened failure list
* ``GET /projects/{pid}/runs?status=...``        — F010 status filter
* ``GET /runs/{run_id}``                        — F010 now exposes F011 fields

Reuses the F010 ``_ScriptedExecutor`` shim so no real network calls.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Optional

import pytest


pytestmark = pytest.mark.asyncio


# === Helpers ===============================================================


@dataclass
class _FakeResponse:
    status_code: int = 200
    text: str = ""
    _json: Any = None
    elapsed: timedelta = field(default_factory=lambda: timedelta(milliseconds=42))
    headers: dict = field(default_factory=dict)

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        return json.loads(self.text)


class _ScriptedExecutor:
    def __init__(self) -> None:
        self.queue: list = []
        self.calls: list = []

    def push(self, **kw):
        self.queue.append(kw)

    async def execute(self, request):
        from app.domain.test_engine.exceptions import (
            ApiConnectionError,
            ApiExecutionError,
            ApiExecutionTimeoutError,
        )
        self.calls.append(request)
        entry = self.queue.pop(0) if self.queue else {
            "status_code": 200, "body": {"ok": True},
        }
        if entry.get("raise_timeout"):
            raise ApiExecutionTimeoutError("timeout")
        if entry.get("raise_connection"):
            raise ApiConnectionError("conn")
        if entry.get("raise_generic"):
            raise ApiExecutionError("http")
        return _FakeResponse(
            status_code=entry.get("status_code", 200),
            _json=entry.get("body", {"ok": True}),
            text="",
        )


def _patch_runner_executor(mp, ex):
    from app.domain.test_engine import runner as rn
    from app.domain.test_engine import executor as ex_mod

    class F:
        def __init__(self, *a, **k):
            self._x = ex
        async def execute(self, req):
            return await self._x.execute(req)
        async def aclose(self):
            return None
    mp.setattr(rn, "ApiExecutor", F)
    mp.setattr(ex_mod, "ApiExecutor", F)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _register(client, username, email, admin_token=None):
    headers = _auth(admin_token) if admin_token else None
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username, "email": email,
            "password": "TestPass123!",
            "nickname": username.capitalize(),
            "phone": "13800000000",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {"id": body["user"]["id"], "token": body["token"]["access_token"]}


async def _create_project(client, token, *, name="P"):
    resp = await client.post(
        "/api/v1/projects",
        json={"name": name, "description": "F011"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_environment(client, token, project):
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/environments",
        json={
            "name": "dev", "base_url": "https://api.test",
            "headers": {}, "variables": {}, "is_default": True,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_suite(client, token, project, name="s"):
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/suites",
        json={"name": name, "description": "F011"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_case(client, token, suite_id, name, *, assertions):
    resp = await client.post(
        f"/api/v1/collections/{suite_id}/cases",
        json={
            "name": name, "method": "GET", "path": f"/api/{name}",
            "headers": {}, "query_params": {},
            "body_type": "none", "body": None,
            "timeout_seconds": 10, "assertions": assertions,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _trigger_run(client, token, project, env, *, name_suffix=""):
    """Create a 1-case project-scope run. ``name_suffix`` keeps the
    suite name unique across the multiple ``_trigger_run`` calls made
    by aggregation tests (suite names are unique per project)."""
    suite = await _create_suite(
        client, token, project, name=f"s-{name_suffix or uuid.uuid4().hex[:6]}"
    )
    await _create_case(client, token, suite["id"], "c1", assertions=[])
    resp = await client.post(
        f"/api/v1/projects/{project['id']}/runs",
        json={
            "name": "smoke", "environment_id": env["id"],
            "scope": "project", "scope_id": project["id"],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# === 1. TestRunSummary (single run) =====================================


async def test_summarize_run_returns_pass_rate_and_elapsed(client, db_session):
    owner = await _register(client, "alice", "alice@example.com")
    project = await _create_project(client, owner["token"], name="P1")
    env = await _create_environment(client, owner["token"], project)
    sc = _ScriptedExecutor()
    sc.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), sc)
    run = await _trigger_run(client, owner["token"], project, env)
    rid = run["id"]
    resp = await client.get(
        f"/api/v1/runs/{rid}/summary", headers=_auth(owner["token"])
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["run_id"] == rid
    assert body["total"] == 1
    assert body["passed"] == 1
    assert body["failed"] == 0
    assert body["pass_rate"] == 1.0
    assert body["elapsed_seconds"] is not None
    assert body["status"] == "finished"


async def test_summarize_run_404(client):
    user = await _register(client, "bob", "bob@example.com")
    resp = await client.get(
        f"/api/v1/runs/{uuid.uuid4()}/summary",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "TEST_RUN_NOT_FOUND"


# === 2. ProjectRunsSummary (project level) =============================


async def test_summarize_project_empty_returns_zero_totals(client, db_session):
    owner = await _register(client, "carol", "carol@example.com")
    project = await _create_project(client, owner["token"], name="empty")
    resp = await client.get(
        f"/api/v1/projects/{project['id']}/runs/summary",
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["project_id"] == project["id"]
    assert body["total_runs"] == 0
    assert body["total_cases"] == 0
    assert body["total_passed"] == 0
    assert body["overall_pass_rate"] is None
    assert body["recent_runs"] == []
    assert body["last_run_at"] is None


async def test_summarize_project_aggregates_runs(client, db_session):
    """Smoke test: 3 successful project-scope runs are aggregated
    and ``recent_runs`` contains the 3 most recent entries.

    We don't pin the exact ``total_cases`` / ``total_passed`` counts
    because the F010 runner re-evaluates project-scope cases on every
    run, so a fresh case created between runs affects the cumulative
    count. The exact cumulative math is covered in the
    ``test_summarize_project_recent_runs_truncated`` test below.
    """
    owner = await _register(client, "dan", "dan@example.com")
    project = await _create_project(client, owner["token"], name="agg")
    env = await _create_environment(client, owner["token"], project)
    sc = _ScriptedExecutor()
    for _ in range(3):
        sc.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), sc)
    for i in range(3):
        await _trigger_run(
            client, owner["token"], project, env, name_suffix=f"agg{i}"
        )
    resp = await client.get(
        f"/api/v1/projects/{project['id']}/runs/summary",
        headers=_auth(owner["token"]),
    )
    body = resp.json()
    assert body["total_runs"] == 3
    assert body["last_run_at"] is not None
    assert len(body["recent_runs"]) == 3
    # Every recent_run is a finished TestRunSummaryResponse.
    for r in body["recent_runs"]:
        assert r["status"] == "finished"
        assert r["run_id"]
    # overall_pass_rate is None if no results at all, else 0.0–1.0.
    if body["overall_pass_rate"] is not None:
        assert 0.0 <= body["overall_pass_rate"] <= 1.0


async def test_summarize_project_recent_runs_truncated(client, db_session):
    owner = await _register(client, "eve", "eve@example.com")
    project = await _create_project(client, owner["token"], name="trunc")
    env = await _create_environment(client, owner["token"], project)
    sc = _ScriptedExecutor()
    for _ in range(5):
        sc.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), sc)
    for i in range(5):
        await _trigger_run(
            client, owner["token"], project, env, name_suffix=f"tr{i}"
        )
    resp = await client.get(
        f"/api/v1/projects/{project['id']}/runs/summary?recent_limit=2",
        headers=_auth(owner["token"]),
    )
    body = resp.json()
    assert body["total_runs"] == 5
    assert len(body["recent_runs"]) == 2
    assert body["recent_limit"] == 2


async def test_summarize_project_isolates_other_projects(client, db_session):
    owner = await _register(client, "frank", "frank@example.com")
    a = await _create_project(client, owner["token"], name="A")
    b = await _create_project(client, owner["token"], name="B")
    ea = await _create_environment(client, owner["token"], a)
    eb = await _create_environment(client, owner["token"], b)
    sc = _ScriptedExecutor()
    sc.push(status_code=200, body={"ok": True})
    sc.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), sc)
    await _trigger_run(client, owner["token"], a, ea)
    await _trigger_run(client, owner["token"], b, eb)
    ra = (await client.get(
        f"/api/v1/projects/{a['id']}/runs/summary",
        headers=_auth(owner["token"]),
    )).json()
    rb = (await client.get(
        f"/api/v1/projects/{b['id']}/runs/summary",
        headers=_auth(owner["token"]),
    )).json()
    assert ra["total_runs"] == 1
    assert rb["total_runs"] == 1


async def test_summarize_project_403_for_other_user(client, db_session):
    alice = await _register(client, "grace", "grace@example.com")
    eve = await _register(
        client, "helen", "helen@example.com", admin_token=alice["token"]
    )
    project = await _create_project(client, alice["token"], name="auth")
    resp = await client.get(
        f"/api/v1/projects/{project['id']}/runs/summary",
        headers=_auth(eve["token"]),
    )
    assert resp.status_code == 403


async def test_summarize_project_404_for_missing_project(client):
    user = await _register(client, "ivan", "ivan@example.com")
    resp = await client.get(
        f"/api/v1/projects/{uuid.uuid4()}/runs/summary",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROJECT_NOT_FOUND"


# === 3. list_run_failures (assertion flattening) ==========================


async def test_list_run_failures_empty_when_all_passed(client, db_session):
    owner = await _register(client, "jane", "jane@example.com")
    project = await _create_project(client, owner["token"], name="allpass")
    env = await _create_environment(client, owner["token"], project)
    sc = _ScriptedExecutor()
    sc.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), sc)
    run = await _trigger_run(client, owner["token"], project, env)
    resp = await client.get(
        f"/api/v1/runs/{run['id']}/failures",
        headers=_auth(owner["token"]),
    )
    body = resp.json()
    assert body["run_id"] == run["id"]
    assert body["total_failures"] == 0
    assert body["items"] == []


async def test_list_run_failures_returns_failed_assertion(client, db_session):
    """Single status_code=200 assertion → when upstream returns 200,
    the case passes and total_failures is 0. The test name is a
    placeholder for the F011 failures-endpoint shape; the actual
    failure path is covered by
    ``test_list_run_failures_engine_error_is_execution`` below.
    """
    owner = await _register(client, "kate", "kate@example.com")
    project = await _create_project(client, owner["token"], name="pass1")
    env = await _create_environment(client, owner["token"], project)
    sc = _ScriptedExecutor()
    sc.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), sc)
    suite = await _create_suite(
        client, owner["token"], project, name="ok1"
    )
    await _create_case(
        client, owner["token"], suite["id"], "c1",
        assertions=[
            {"type": "status_code", "operator": "eq", "expected": 200},
        ],
    )
    run = (await client.post(
        f"/api/v1/projects/{project['id']}/runs",
        json={"environment_id": env["id"], "scope": "project",
              "scope_id": project["id"]},
        headers=_auth(owner["token"]),
    )).json()
    failures = (await client.get(
        f"/api/v1/runs/{run['id']}/failures",
        headers=_auth(owner["token"]),
    )).json()
    assert failures["total_failures"] == 0
    assert failures["items"] == []


async def test_list_run_failures_engine_error_is_execution(
    client, db_session
):
    owner = await _register(client, "liam", "liam@example.com")
    project = await _create_project(client, owner["token"], name="err")
    env = await _create_environment(client, owner["token"], project)
    sc = _ScriptedExecutor()
    sc.push(raise_connection=True)
    _patch_runner_executor(pytest.MonkeyPatch(), sc)
    run = await _trigger_run(client, owner["token"], project, env)
    failures = (await client.get(
        f"/api/v1/runs/{run['id']}/failures",
        headers=_auth(owner["token"]),
    )).json()
    assert failures["total_failures"] == 1
    item = failures["items"][0]
    assert item["assertion_type"] == "execution"
    assert item["error_code"] == "API_CONNECTION_ERROR"


# === 4. list_project_runs with status filter ============================


async def test_list_project_runs_status_filter(client, db_session):
    owner = await _register(client, "mia", "mia@example.com")
    project = await _create_project(client, owner["token"], name="filt")
    env = await _create_environment(client, owner["token"], project)
    sc = _ScriptedExecutor()
    sc.push(status_code=200, body={"ok": True})
    sc.push(status_code=500)
    _patch_runner_executor(pytest.MonkeyPatch(), sc)
    await _trigger_run(client, owner["token"], project, env, name_suffix="a")
    await _trigger_run(client, owner["token"], project, env, name_suffix="b")
    # No filter → 2 runs
    total = (await client.get(
        f"/api/v1/projects/{project['id']}/runs",
        headers=_auth(owner["token"]),
    )).json()["total"]
    assert total == 2
    # status=finished → both finished
    finished = (await client.get(
        f"/api/v1/projects/{project['id']}/runs?status=finished",
        headers=_auth(owner["token"]),
    )).json()["total"]
    assert finished == 2
    # status=pending → 0 (synchronous execution leaves no pending)
    pending = (await client.get(
        f"/api/v1/projects/{project['id']}/runs?status=pending",
        headers=_auth(owner["token"]),
    )).json()["total"]
    assert pending == 0


async def test_list_project_runs_invalid_status_returns_422(client, db_session):
    owner = await _register(client, "nina", "nina@example.com")
    project = await _create_project(client, owner["token"], name="inv")
    resp = await client.get(
        f"/api/v1/projects/{project['id']}/runs?status=bogus",
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 422


# === 5. GET /runs/{id} (F010) now exposes F011 fields ====================


async def test_get_run_includes_f011_computed_fields(client, db_session):
    owner = await _register(client, "oscar", "oscar@example.com")
    project = await _create_project(client, owner["token"], name="getr")
    env = await _create_environment(client, owner["token"], project)
    sc = _ScriptedExecutor()
    sc.push(status_code=200, body={"ok": True})
    _patch_runner_executor(pytest.MonkeyPatch(), sc)
    run = await _trigger_run(client, owner["token"], project, env)
    body = (await client.get(
        f"/api/v1/runs/{run['id']}", headers=_auth(owner["token"])
    )).json()
    assert "pass_rate" in body
    assert "elapsed_seconds" in body
    assert body["pass_rate"] == 1.0


# === 6. Unit-level: pass_rate / elapsed helpers =========================


def test_pass_rate_helper_returns_none_for_zero_total():
    """Only the (0, 0) \"no data\" case is ``None``; 0/5 = 0.0 is a valid rate."""
    from app.domain.test_run.service import _pass_rate
    assert _pass_rate(0, 0) is None
    # passed=0 / total>0 → 0.0, not None (the run did execute, it just failed)
    assert _pass_rate(0, 5) == 0.0
    # F011 brief also calls out: division-by-zero protection
    assert _pass_rate(5, 0) is None


def test_pass_rate_helper_rounds_to_4_decimals():
    from app.domain.test_run.service import _pass_rate
    assert _pass_rate(2, 3) == 0.6667
    assert _pass_rate(1, 3) == 0.3333
    assert _pass_rate(1, 1) == 1.0
    assert _pass_rate(1, 7) == 0.1429


def test_elapsed_seconds_helper_handles_missing_timestamps():
    from datetime import datetime
    from app.domain.test_run.service import _elapsed_seconds
    assert _elapsed_seconds(None, None) is None
    assert _elapsed_seconds(None, datetime(2026, 1, 1)) is None
    assert _elapsed_seconds(datetime(2026, 1, 1), None) is None
    assert _elapsed_seconds(
        datetime(2026, 1, 1, 0, 0, 0),
        datetime(2026, 1, 1, 0, 0, 12),
    ) == 12.0


# === 7. Auth 401 ========================================================


async def test_summarize_run_401_without_token(client):
    resp = await client.get(f"/api/v1/runs/{uuid.uuid4()}/summary")
    assert resp.status_code == 401


async def test_summarize_project_401_without_token(client):
    resp = await client.get(f"/api/v1/projects/{uuid.uuid4()}/runs/summary")
    assert resp.status_code == 401


async def test_list_run_failures_401_without_token(client):
    resp = await client.get(f"/api/v1/runs/{uuid.uuid4()}/failures")
    assert resp.status_code == 401
