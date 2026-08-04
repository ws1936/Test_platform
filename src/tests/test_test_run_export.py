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
            "scope_id": uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
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
            "triggered_by": uuid.UUID("ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb"),
        },
    )()


def _make_result(
    status="passed",
    elapsed_ms=42,
    error_message=None,
    *,
    case_name="case-x",
    case_path="/api/x",
    case_method="GET",
    request_snapshot=None,
    response_snapshot=None,
    assertions_snapshot=None,
):
    """手工构造一个 ApiTestResult-like 对象。

    关键字参数项可以是默认值（让基本测试不关心这些字段），
    XSS / 脱敏 / 截断等专项测试可以手传 dict 覆盖。
    """
    return type(
        "FakeResult",
        (),
        {
            "id": uuid.uuid4(),
            "test_case_id": uuid.uuid4(),
            "case_name": case_name,
            "case_method": case_method,
            "case_path": case_path,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "error_code": None,
            "error_message": error_message,
            "started_at": datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
            "finished_at": datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
            "request_snapshot": request_snapshot,
            "response_snapshot": response_snapshot,
            "assertions_snapshot": assertions_snapshot,
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
    # 透传 None 给三个 snapshot 字段——这个测试只关心 XSS 转义，不关心快照内容。
    evil = _make_result(
        case_name='<script>alert("xss")</script>',
        case_path="/api/<x>",
        error_message='a & b "c"',
        request_snapshot=None,
        response_snapshot=None,
        assertions_snapshot=None,
    )
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


# ---------------------------------------------------------------------------
# F015 专项：脱敏 / 完整快照 / 格式约定
# ---------------------------------------------------------------------------


def test_build_payload_includes_full_snapshots():
    """JSON 导出必须包含 request/response/assertions 三个快照以满足 PRD §5.8。"""
    req_snap = {
        "method": "GET",
        "url": "https://api.test/api/x",
        "headers": {"Authorization": "Bearer SECRET"},
        "params": {},
        "body": None,
        "timeout": 30,
        "variables_used": {},
    }
    resp_snap = {
        "status_code": 200,
        "headers": {
            "Authorization": "Bearer SECRET",  # 响应头里的敏感头也要脱敏
            "Set-Cookie": "session=abc",
            "Content-Type": "application/json",
        },
        "body": '{"ok":true}',
        "body_truncated": False,
        "elapsed_ms": 42,
    }
    asserts_snap = [
        {"type": "status_code", "operator": "eq", "expected": 200, "passed": True},
    ]
    result = _make_result(
        request_snapshot=req_snap,
        response_snapshot=resp_snap,
        assertions_snapshot=asserts_snap,
    )
    payload = build_payload(_make_run(), [result])
    parsed = render_json(payload)
    import json as _json

    out = _json.loads(parsed)
    item = out["results"][0]
    assert item["request_snapshot"] == req_snap
    assert item["assertions_snapshot"] == asserts_snap
    # response_snapshot 的 headers 被脱敏，body / status_code / elapsed_ms 不变
    sanitized_resp = item["response_snapshot"]
    assert sanitized_resp["status_code"] == 200
    assert sanitized_resp["body"] == '{"ok":true}'
    assert sanitized_resp["elapsed_ms"] == 42
    assert sanitized_resp["body_truncated"] is False
    assert "Authorization" not in sanitized_resp["headers"]
    assert "Set-Cookie" not in sanitized_resp["headers"]
    assert "Set-Cookie".lower() not in {k.lower() for k in sanitized_resp["headers"]}
    assert sanitized_resp["headers"]["Content-Type"] == "application/json"


def test_build_payload_preserves_sanitized_request_snapshot():
    """F015 信任 F010 持久化层的脱敏（快照在写入 DB 时已被 _sanitize_headers
    处理）。F015 不应再二次脱敏 request_snapshot，避免意外改动业务字段。
    但 response_snapshot.headers 仍走 F015 自己的脱敏路径，因为 F010
    在写入时未脱敏 response headers（响应侧可能含 Set-Cookie / 业务自定义
    敏感头）。本测试锁定：request_snapshot 原样保留；response.headers
    会被 F015 再次脱敏。
    """
    # F010 写入 DB 时已脱敏：Authorization 已在持久化前被去掉。
    req_snap = {
        "method": "POST",
        "url": "https://api.test/login",
        "headers": {"X-Custom": "ok"},  # 没有 Authorization
        "params": {},
        "body": None,
        "timeout": 30,
        "variables_used": {},
    }
    resp_snap = {
        "status_code": 200,
        "headers": {"Authorization": "Bearer SECRET", "X-Trace": "abc"},
        "body": "{}",
        "body_truncated": False,
        "elapsed_ms": 10,
    }
    result = _make_result(
        request_snapshot=req_snap,
        response_snapshot=resp_snap,
        assertions_snapshot=None,
    )
    payload = build_payload(_make_run(), [result])
    import json as _json
    item = _json.loads(render_json(payload))["results"][0]
    # request_snapshot 原样保留（已是 F010 脱敏后的产物）
    assert item["request_snapshot"] == req_snap
    # response.headers 被 F015 脱敏
    assert "Authorization" not in item["response_snapshot"]["headers"]
    assert item["response_snapshot"]["headers"]["X-Trace"] == "abc"


def test_payload_handles_missing_or_null_snapshots_gracefully():
    """容错：response_snapshot=None / headers 为空 / snapshot 字段缺失。"""
    result = _make_result(
        request_snapshot=None,
        response_snapshot=None,
        assertions_snapshot=None,
    )
    payload = build_payload(_make_run(), [result])
    import json as _json
    item = _json.loads(render_json(payload))["results"][0]
    assert item["request_snapshot"] is None
    assert item["response_snapshot"] is None
    assert item["assertions_snapshot"] is None

    # response_snapshot 有但 headers 为空
    result2 = _make_result(
        response_snapshot={"status_code": 200, "headers": {}, "body": "x"},
    )
    item2 = _json.loads(render_json(build_payload(_make_run(), [result2])))["results"][0]
    # headers 空 dict 不报错，原样返回
    assert item2["response_snapshot"]["headers"] == {}
    assert item2["response_snapshot"]["status_code"] == 200


def test_html_export_does_not_leak_authorization():
    """HTML 报告不包含请求/响应快照，只展示摘要信息。
    即使 test_snapshot 中有 Authorization，HTML 不该出现（防 XSS / 信息泄露）。
    """
    req_snap = {
        "method": "GET",
        "url": "https://api.test/api/private",
        "headers": {"Authorization": "Bearer SUPER_SECRET_TOKEN"},
        "params": {},
        "body": None,
        "timeout": 30,
        "variables_used": {},
    }
    resp_snap = {
        "status_code": 403,
        "headers": {"WWW-Authenticate": "Bearer"},
        "body": "forbidden",
        "body_truncated": False,
        "elapsed_ms": 10,
    }
    result = _make_result(
        status="failed",
        request_snapshot=req_snap,
        response_snapshot=resp_snap,
        assertions_snapshot=[],
        error_message="HTTP 403",  # HTML 只展示 error_message，不展示 response body
    )
    payload = build_payload(_make_run(), [result])
    html = render_html(payload)
    # HTML 表格只展示 case_name / case_method / case_path / elapsed / error_message
    # 不展示 request/response body/header；error_message 被展示。
    assert "SUPER_SECRET_TOKEN" not in html
    assert "Authorization" not in html  # request header 名也不该出现
    assert "WWW-Authenticate" not in html
    assert "HTTP 403" in html  # error_message 被展示
    assert "WWW-Authenticate".lower() not in html.lower()
    assert "forbidden" not in html  # response body 不会出现在 HTML
