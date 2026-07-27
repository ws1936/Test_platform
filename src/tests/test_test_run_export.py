"""F015 报告导出 — exporter + /runs/{run_id}/export 端点的单测。

覆盖：
- exporter.export_run 两种 format (json, html) 渲染正确
- exporter.export_run 拒绝非法 format
- TestRunService.export_run 鉴权 + delegate
- /runs/{run_id}/export 端点返回 200/400/401/403/404
- 鉴权：未登录返回 401；非 owner 非 superuser 返回 403
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest

from app.common.security import hash_password
from app.domain.environment.model import ApiEnvironment
from app.domain.environment.repository import EnvironmentRepository
from app.domain.project.model import ApiProject
from app.domain.project.repository import ProjectRepository
from app.domain.role.model import Role
from app.domain.test_run.exporter import (
    build_payload,
    esc,
    export_run as exporter_export_run,
    render_html,
    render_json,
)
from app.domain.user.model import User
from app.domain.user.repository import UserRepository


# ---------------------------------------------------------------------------
# Exporter 单元测试（不需要 DB）
# ---------------------------------------------------------------------------


def _make_run():
    """手工构造一个 ApiTestRun-like 对象（F015 只要属性）。"""
    return type(
        "FakeRun",
        (),
        {
            "id": uuid.UUID("11111111-2222-3333-4444-555555555555"),
            "name": "smoke",
            "scope": "project",
            "status": "finished",
            "total": 2,
            "passed": 1,
            "failed": 1,
            "error": 0,
            "skipped": 0,
            "started_at": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            "finished_at": datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
            "environment_id": uuid.uuid4(),
            "project_id": uuid.uuid4(),
        },
    )()


def _make_result(status="passed", elapsed_ms=42, error_message=None):
    return type(
        "FakeResult",
        (),
        {
            "id": uuid.uuid4(),
            "test_case_id": uuid.uuid4(),
            "case_name": "case-x",
            "case_method": "GET",
            "case_path": "/api/x",
            "status": status,
            "elapsed_ms": elapsed_ms,
            "error_code": None,
            "error_message": error_message,
            "started_at": datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
            "finished_at": datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
        },
    )()


def test_esc_basic():
    assert esc('a&b<c>d"e') == 'a&amp;b&lt;c&gt;d&quot;e'
    assert esc(None) == ""
    assert esc(123) == "123"


def test_render_json_includes_run_and_results():
    run = _make_run()
    results = [_make_result(), _make_result("failed", 80, "boom")]
    payload = build_payload(run, results)
    out = render_json(payload)
    parsed = json.loads(out)
    assert parsed["run"]["id"] == str(run.id)
    assert parsed["run"]["total"] == 2
    assert parsed["run"]["passed"] == 1
    assert parsed["run"]["failed"] == 1
    assert len(parsed["results"]) == 2
    assert parsed["results"][1]["error_message"] == "boom"


def test_render_html_basic():
    run = _make_run()
    results = [_make_result()]
    payload = build_payload(run, results)
    html = render_html(payload)
    assert html.startswith("<!DOCTYPE html>")
    assert "Run Report" in html
    assert "smoke" in html
    assert "/api/x" in html
    assert "Total" in html
    assert "Pass Rate" in html
    assert "50.0%" in html  # 1/2 = 50%
    # 不应该含 <script（XSS 防护）
    assert "<script" not in html.lower()


def test_render_html_escapes_user_input():
    """XSS：用户输入的 < > & " 必须被 escape。"""
    run = _make_run()
    evil = type("R", (), {
        "id": uuid.uuid4(),
        "test_case_id": uuid.uuid4(),
        "case_name": '<script>alert("xss")</script>',
        "case_method": "GET",
        "case_path": "/api/<x>",
        "status": "passed",
        "elapsed_ms": 10,
        "error_code": None,
        "error_message": 'a & b "c"',
        "started_at": None,
        "finished_at": None,
    })()
    payload = build_payload(run, [evil])
    html = render_html(payload)
    # Raw user-controlled markup should not appear; escaped text should.
    assert "<script>alert" not in html
    assert "&lt;script&gt;alert" in html
    assert "&quot;xss&quot;" in html
    assert "a &amp; b" in html
    # Angle brackets in the path are escaped as text.
    assert "/api/&lt;x&gt;" in html


def test_exporter_export_run_returns_correct_triple_for_html():
    run = _make_run()
    results = [_make_result()]
    content, media, fname = exporter_export_run(run, results, "html")
    assert media == "text/html; charset=utf-8"
    assert fname.endswith(".html")
    assert "smoke" in fname or run.started_at.strftime("%Y%m%d") in fname
    assert "<!DOCTYPE html>" in content


def test_exporter_export_run_returns_correct_triple_for_json():
    run = _make_run()
    results = [_make_result()]
    content, media, fname = exporter_export_run(run, results, "json")
    assert media == "application/json; charset=utf-8"
    assert fname.endswith(".json")
    parsed = json.loads(content)
    assert "run" in parsed and "results" in parsed


def test_exporter_export_run_rejects_bad_format():
    run = _make_run()
    results = [_make_result()]
    with pytest.raises(ValueError, match="format must be"):
        exporter_export_run(run, results, "xml")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="format must be"):
        exporter_export_run(run, results, "")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 服务 / 端点 集成测试（需要 DB + conftest）
# ---------------------------------------------------------------------------


async def _create_user(db_session, *, username: str, email: str, is_superuser=False) -> User:
    role = Role(
        id=uuid.uuid4(),
        name=f"role_{uuid.uuid4().hex[:8]}",
        description="f015 test role",
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


async def _create_project_and_env(db_session, *, owner: User):
    project = ApiProject(
        id=uuid.uuid4(),
        name="f015-proj",
        description="f015",
        owner_id=owner.id,
    )
    db_session.add(project)
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
    return project, env


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, username: str, email: str, admin_token=None):
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


async def test_export_run_endpoint_returns_json(client, db_session):
    from datetime import datetime, timezone
    from app.domain.test_run.model import ApiTestRun

    owner = await _register(client, "f015a", "f015a@example.com")
    user = await UserRepository(db_session).get_by_id(uuid.UUID(owner["id"]))
    project, env = await _create_project_and_env(db_session, owner=user)

    run = ApiTestRun(
        id=uuid.uuid4(),
        project_id=project.id,
        environment_id=env.id,
        name="f015-run",
        scope="project",
        status="finished",
        triggered_by=user.id,
        total=2,
        passed=1,
        failed=1,
        error=0,
        skipped=0,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/runs/{run.id}/export",
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert body["run"]["id"] == str(run.id)
    assert body["run"]["name"] == "f015-run"
    # 文件名 attachment
    assert "attachment" in resp.headers.get("content-disposition", "")


async def test_export_run_endpoint_returns_html(client, db_session):
    from datetime import datetime, timezone
    from app.domain.test_run.model import ApiTestRun

    owner = await _register(client, "f015b", "f015b@example.com")
    user = await UserRepository(db_session).get_by_id(uuid.UUID(owner["id"]))
    project, env = await _create_project_and_env(db_session, owner=user)
    run = ApiTestRun(
        id=uuid.uuid4(),
        project_id=project.id,
        environment_id=env.id,
        name="f015-html",
        scope="project",
        status="finished",
        triggered_by=user.id,
        total=1,
        passed=1,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/runs/{run.id}/export?format=html",
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/html")
    assert "<!DOCTYPE html>" in resp.text
    assert "f015-html" in resp.text


async def test_export_run_rejects_bad_format(client, db_session):
    from datetime import datetime, timezone
    from app.domain.test_run.model import ApiTestRun

    owner = await _register(client, "f015c", "f015c@example.com")
    user = await UserRepository(db_session).get_by_id(uuid.UUID(owner["id"]))
    project, env = await _create_project_and_env(db_session, owner=user)
    run = ApiTestRun(
        id=uuid.uuid4(),
        project_id=project.id,
        environment_id=env.id,
        name="f015-bad",
        scope="project",
        status="finished",
        triggered_by=user.id,
        total=1,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/runs/{run.id}/export?format=xml",
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 422  # Query pattern 校验


async def test_export_run_requires_auth(client, db_session):
    resp = await client.get(f"/api/v1/runs/{uuid.uuid4()}/export")
    assert resp.status_code == 401


async def test_export_run_404_for_missing_run(client, db_session):
    owner = await _register(client, "f015d", "f015d@example.com")
    resp = await client.get(
        f"/api/v1/runs/{uuid.uuid4()}/export",
        headers=_auth(owner["token"]),
    )
    assert resp.status_code == 404


async def test_export_run_403_for_other_user(client, db_session):
    from datetime import datetime, timezone
    from app.domain.test_run.model import ApiTestRun

    alice = await _register(client, "f015alice", "f015alice@example.com")
    bob = await _register(
        client, "f015bob", "f015bob@example.com", admin_token=alice["token"]
    )
    alice_user = await UserRepository(db_session).get_by_id(uuid.UUID(alice["id"]))
    project, env = await _create_project_and_env(db_session, owner=alice_user)
    run = ApiTestRun(
        id=uuid.uuid4(),
        project_id=project.id,
        environment_id=env.id,
        name="f015-private",
        scope="project",
        status="finished",
        triggered_by=alice_user.id,
        total=1,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    await db_session.commit()

    # Bob 是非 owner 非 superuser
    resp = await client.get(
        f"/api/v1/runs/{run.id}/export",
        headers=_auth(bob["token"]),
    )
    assert resp.status_code == 403
