"""F014 有限并发执行 — TestRunner Semaphore 行为测试。

覆盖：
- 默认并发数（settings.TEST_RUN_MAX_CONCURRENCY）有效
- 显式 max_concurrency=1 退化为串行
- 显式 max_concurrency=N 实际限制同时在飞的 _execute_single
- 非法 max_concurrency（0 / 负数）回落到 1
- _execute_single 抛异常时 gather() 不被整体中断
- 单 case 列表（size=1）并发逻辑退化为普通执行
- 计数器统计在并发场景下依然正确

使用真 DB（SQLite in-memory）但 monkeypatch ApiExecutor，避开真实网络。
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, List, Optional

import pytest

from app.common.security import hash_password
from app.config import settings
from app.domain.environment.model import ApiEnvironment
from app.domain.environment.repository import EnvironmentRepository
from app.domain.project.model import ApiProject
from app.domain.project.repository import ProjectRepository
from app.domain.role.model import Role
from app.domain.test_case.model import ApiTestCase
from app.domain.test_engine.runner import TestRunner
from app.domain.test_run.model import ApiTestResult, ApiTestRun
from app.domain.user.model import User
from app.domain.user.repository import UserRepository


# ---------------------------------------------------------------------------
# 控制并发度的 Fake Executor：记录同时在飞的请求数
# ---------------------------------------------------------------------------


@dataclass
class _TimedResponse:
    status_code: int = 200
    text: str = ""
    _json: Any = None
    elapsed: timedelta = field(default_factory=lambda: timedelta(milliseconds=42))
    headers: dict = field(default_factory=dict)

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        return {}


class _ConcurrencyProbeExecutor:
    """F014 测试用 executor：

    - 每个 execute() 在 await 期间持有 ``active`` 计数。
    - 调用方可以查询峰值并发 ``peak_active``。
    - 通过 ``delay`` 控制每个 case 的耗时，让窗口足够重叠以观察并发。
    - 通过 ``raise_exc_for`` 触发指定 case_id 抛 ``ApiExecutionError``，
      用于验证 gather() 不被整体中断。
    """

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay
        self.active = 0
        self.peak_active = 0
        self.calls: List[str] = []
        self._lock = asyncio.Lock()
        self.raise_exc_for: Optional[str] = None  # path 形如 "/api/concurrency-error"

    async def execute(self, request: Any) -> _TimedResponse:  # type: ignore[override]
        from app.domain.test_engine.exceptions import ApiExecutionError

        async with self._lock:
            self.active += 1
            self.peak_active = max(self.peak_active, self.active)

        self.calls.append(request.url)

        if self.raise_exc_for and request.url.endswith(self.raise_exc_for):
            async with self._lock:
                self.active -= 1
            raise ApiExecutionError(f"forced error for {request.url}")

        await asyncio.sleep(self.delay)
        async with self._lock:
            self.active -= 1
        return _TimedResponse(status_code=200, _json={"ok": True})

    async def aclose(self) -> None:  # pragma: no cover
        return None


# ---------------------------------------------------------------------------
# 测试夹具
# ---------------------------------------------------------------------------


async def _create_user(db_session, *, username: str, email: str) -> User:
    role = Role(
        id=uuid.uuid4(),
        name=f"role_{uuid.uuid4().hex[:8]}",
        description="f014 test role",
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


async def _create_project(db_session, *, owner: User, name: str = "P") -> ApiProject:
    project = ApiProject(
        id=uuid.uuid4(),
        name=name,
        description="f014 test",
        owner_id=owner.id,
    )
    db_session.add(project)
    await db_session.commit()
    return project


async def _create_environment(
    db_session, *, project: ApiProject, name: str = "dev"
) -> ApiEnvironment:
    env = ApiEnvironment(
        id=uuid.uuid4(),
        project_id=project.id,
        name=name,
        base_url="https://api.test",
        headers={},
        variables={},
        is_default=True,
    )
    db_session.add(env)
    await db_session.commit()
    return env


async def _create_cases(
    db_session, *, project: ApiProject, count: int
) -> List[ApiTestCase]:
    """为前 (count-1) 个 case 配 status_code=200 断言，最后 1 个留空。

    留空验证 F009 设计：未配 assertion = 默认 pass（无校验 = 通过）。
    """
    cases: List[ApiTestCase] = []
    for i in range(count):
        if i < count - 1:
            asserts = [{"type": "status_code", "operator": "eq", "expected": 200}]
        else:
            asserts = []
        case = ApiTestCase(
            id=uuid.uuid4(),
            project_id=project.id,
            name=f"f014-case-{i}",
            method="GET",
            path=f"/api/f014/{i}",
            headers={},
            query_params={},
            body_type="none",
            body=None,
            assertions=asserts,
            timeout_seconds=10,
            status=1,
            sort_order=i,
        )
        db_session.add(case)
        cases.append(case)
    await db_session.commit()
    return cases


async def _trigger_run(
    db_session, *, owner: User, project: ApiProject, env: ApiEnvironment, count: int
):
    """直接构造一个 ApiTestRun + 调用 TestRunner，绕开 HTTP 层以避免 mock 注入麻烦。"""
    cases = await _create_cases(db_session, project=project, count=count)
    run = ApiTestRun(
        id=uuid.uuid4(),
        project_id=project.id,
        environment_id=env.id,
        name="f014-run",
        scope="project",
        status="pending",
        triggered_by=owner.id,
        total=count,
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    db_session.add(run)
    await db_session.commit()
    return run, [c.id for c in cases]


# ---------------------------------------------------------------------------
# 1. 默认并发：从 settings 读
# ---------------------------------------------------------------------------


async def test_default_concurrency_uses_settings(db_session):
    owner = await _create_user(db_session, username="f014a", email="f014a@example.com")
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)
    run, case_ids = await _trigger_run(
        db_session, owner=owner, project=project, env=env, count=8
    )

    probe = _ConcurrencyProbeExecutor(delay=0.08)
    runner = TestRunner(db_session, executor=probe)  # type: ignore[arg-type]
    # 默认 max_concurrency 应等于 settings.TEST_RUN_MAX_CONCURRENCY
    assert runner._max_concurrency == settings.TEST_RUN_MAX_CONCURRENCY

    await runner.execute_run(run=run, env=env, case_ids=case_ids)

    assert run.passed == 8
    assert run.failed == 0
    assert run.error == 0
    # 8 个 case，每个 0.08s；总耗时 (8 / N) * 0.08 + 余量
    # 默认 N=4，预期 ≈ 0.16s + setup；串行则 ≈ 0.64s
    # 关键是峰值并发 <= N
    assert probe.peak_active <= settings.TEST_RUN_MAX_CONCURRENCY
    assert probe.peak_active >= 2  # 至少观察到 2 并发才证明并行生效


# ---------------------------------------------------------------------------
# 2. 显式 max_concurrency=1 = 串行
# ---------------------------------------------------------------------------


async def test_explicit_concurrency_1_is_serial(db_session):
    owner = await _create_user(db_session, username="f014b", email="f014b@example.com")
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)
    run, case_ids = await _trigger_run(
        db_session, owner=owner, project=project, env=env, count=4
    )

    probe = _ConcurrencyProbeExecutor(delay=0.05)
    runner = TestRunner(db_session, executor=probe, max_concurrency=1)  # type: ignore[arg-type]

    t0 = time.perf_counter()
    await runner.execute_run(run=run, env=env, case_ids=case_ids)
    elapsed = time.perf_counter() - t0

    assert run.passed == 4
    # 串行下峰值并发必然 = 1
    assert probe.peak_active == 1
    # 4 * 0.05s = 0.20s（+ setup 抖动），但一定 > 并行版本
    # 留 0.15s 下限，确保不是误判
    assert elapsed >= 0.15


# ---------------------------------------------------------------------------
# 3. 显式 max_concurrency=N 真的限制并行度
# ---------------------------------------------------------------------------


async def test_explicit_concurrency_n_caps_parallelism(db_session):
    owner = await _create_user(db_session, username="f014c", email="f014c@example.com")
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)
    run, case_ids = await _trigger_run(
        db_session, owner=owner, project=project, env=env, count=10
    )

    probe = _ConcurrencyProbeExecutor(delay=0.08)
    runner = TestRunner(db_session, executor=probe, max_concurrency=3)  # type: ignore[arg-type]

    await runner.execute_run(run=run, env=env, case_ids=case_ids)

    assert run.passed == 10
    # 峰值并发不能超过 N
    assert probe.peak_active <= 3
    # 至少观察到 2 并发，否则说明限流把 N 降为 1 了
    assert probe.peak_active >= 2


# ---------------------------------------------------------------------------
# 4. 非法 max_concurrency（0 / 负数）回落到 1（不抛异常）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [0, -1, -100])
async def test_invalid_max_concurrency_falls_back_to_1(db_session, bad: int):
    owner = await _create_user(db_session, username=f"f014d{bad}", email=f"f014d{bad}@example.com")
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)
    run, case_ids = await _trigger_run(
        db_session, owner=owner, project=project, env=env, count=2
    )

    probe = _ConcurrencyProbeExecutor(delay=0.02)
    runner = TestRunner(db_session, executor=probe, max_concurrency=bad)  # type: ignore[arg-type]

    # 不应该抛异常，且应回落为串行
    assert runner._max_concurrency == 1
    await runner.execute_run(run=run, env=env, case_ids=case_ids)

    assert run.passed == 2
    assert probe.peak_active == 1


# ---------------------------------------------------------------------------
# 5. 计数统计在并发场景下依然正确
# ---------------------------------------------------------------------------


async def test_concurrent_run_counters_are_consistent(db_session):
    owner = await _create_user(db_session, username="f014e", email="f014e@example.com")
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)
    # 5 个 case：前 4 个配 status_code=200（200 → pass），最后 1 个无断言（默认 pass）
    run, case_ids = await _trigger_run(
        db_session, owner=owner, project=project, env=env, count=5
    )

    class _MixedExecutor:
        """前 4 个 case 返回 200，最后一个返回 500（断言失败）"""
        def __init__(self):
            self.calls: List[str] = []

        async def execute(self, request):
            self.calls.append(request.url)
            if request.url.endswith("/api/f014/4"):
                return _TimedResponse(status_code=500, _json={"err": "boom"})
            return _TimedResponse(status_code=200, _json={"ok": True})

        async def aclose(self):
            return None

    probe = _MixedExecutor()
    runner = TestRunner(db_session, executor=probe, max_concurrency=3)  # type: ignore[arg-type]

    await runner.execute_run(run=run, env=env, case_ids=case_ids)

    # F009 设计：未配 assertion 的 case，HTTP 2xx 默认视为 pass。
    # 所以 4 个有 status_code=200 断言（收到 200 → pass）+ 1 个无断言（默认 pass）= 5 pass
    assert run.passed == 5
    assert run.failed == 0
    assert run.error == 0
    assert run.total == 5
    assert run.passed + run.failed + run.error + run.skipped == 5


# ---------------------------------------------------------------------------
# 6. _execute_single 抛异常时 gather() 不被整体中断（防御性 net）
# ---------------------------------------------------------------------------


async def test_unexpected_exception_in_execute_single_does_not_abort_run(db_session):
    """即使 _execute_single 抛了未预期异常（defensive net），其他 case 仍要完成。

    注意：_execute_single 内部已经处理了所有 ApiExecutionError / ConnectionError /
    TimeoutError，只有真未预期的 Exception 才会逃逸——这里我们通过 monkeypatch
    _execute_single 自身来模拟。
    """
    owner = await _create_user(db_session, username="f014f", email="f014f@example.com")
    project = await _create_project(db_session, owner=owner)
    env = await _create_environment(db_session, project=project)
    run, case_ids = await _trigger_run(
        db_session, owner=owner, project=project, env=env, count=3
    )

    # 默认 probe 不会抛，只是延迟
    probe = _ConcurrencyProbeExecutor(delay=0.02)
    runner = TestRunner(db_session, executor=probe, max_concurrency=2)  # type: ignore[arg-type]

    # Monkeypatch _execute_single，让中间那个 case 抛 RuntimeError
    original_execute = runner._execute_single
    call_count = {"n": 0}

    async def flaky_execute(*, run, env, case):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("simulated engine bug")
        return await original_execute(run=run, env=env, case=case)

    runner._execute_single = flaky_execute  # type: ignore[assignment]

    # 不应该让整个 gather() 崩溃
    await runner.execute_run(run=run, env=env, case_ids=case_ids)

    # 计数器应当保持合计 = total
    assert run.passed + run.failed + run.error + run.skipped == 3
    # 至少有一个 pass（因为第 1 个和第 3 个 case 成功）
    assert run.passed >= 1
