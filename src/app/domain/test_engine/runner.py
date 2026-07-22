"""TestRunner — orchestrator that drives one full execution run (F010).

This module glues together the four engine pieces from
ARCHITECTURE.md §3.4:

    ``RequestBuilder`` → ``ApiExecutor`` → ``evaluate_all`` (F009)
                                ↓
                       ``ApiTestResult`` persisted

A :class:`TestRunner` is constructed **per run** so each batch has
its own :class:`ApiExecutor` (and therefore its own
:class:`httpx.AsyncClient` lifecycle). One failure inside a case
never aborts the rest of the run — counters are accumulated at the
end, matching the F009 "do not short-circuit" contract.

Snapshot policy
---------------
Every persisted :class:`ApiTestResult` carries:

* ``request_snapshot`` — method / URL / headers / params / body /
  timeout (built from the *resolved* request, i.e. after variable
  substitution). Sensitive headers (``Authorization``, ``Cookie``,
  …) are stripped via :func:`_sanitize_headers`.
* ``response_snapshot`` — status / headers / truncated body / elapsed
  ms. Bodies larger than 64 KiB are truncated and the
  ``body_truncated`` flag is set so the report (F011) can show "…
  +N bytes hidden".
* ``assertions_snapshot`` — JSON-friendly list of
  :class:`AssertionResult` payloads.

This matches PRD §5.8 ("结果详情: 实际请求、响应、断言结果、错误信息")
and AI_RULES §8 ("API 测试结果必须保存请求、响应和断言快照").
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.environment.model import ApiEnvironment
from app.domain.suite.model import ApiSuiteCase
from app.domain.test_case.model import ApiTestCase
from app.domain.test_engine.assertions import AssertionResult, evaluate_all
from app.domain.test_engine.exceptions import (
    ApiConnectionError,
    ApiExecutionError,
    ApiExecutionTimeoutError,
)
from app.domain.test_engine.executor import ApiExecutor
from app.domain.test_engine.request_builder import BuiltRequest, RequestBuilder
from app.domain.test_run.model import ApiTestResult, ApiTestRun
from app.domain.test_run.repository import TestResultRepository, TestRunRepository
from app.services.variable_substitutor import substitute


logger = logging.getLogger(__name__)


# 64 KiB — a body larger than this gets truncated in ``response_snapshot``.
_MAX_RESPONSE_BODY_BYTES = 65_536


# Headers we never persist. Matches the AI_RULES §10 / §11 rules about
# keeping secrets out of stored data.
_SENSITIVE_HEADERS: frozenset[str] = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-auth-token",
        "x-api-key",
        "x-csrf-token",
    }
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


class TestRunner:
    """Drive one :class:`ApiTestRun` from start to finish.

    Lifecycle::

        run = ApiTestRun(...)           # status="pending"
        runner = TestRunner(session)
        await runner.execute_run(...)   # status flips: pending → running → finished
        # every case now has an ApiTestResult row attached to ``run``

    The runner is the only place that touches both the engine
    components and the database in F010. Splitting orchestration
    from the per-case work (``_execute_single``) keeps the per-case
    loop easy to unit-test with a faked :class:`ApiExecutor`.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        executor: Optional[ApiExecutor] = None,
        max_concurrency: Optional[int] = None,
    ) -> None:
        self.session = session
        self.run_repo = TestRunRepository(session)
        self.result_repo = TestResultRepository(session)
        self.executor = executor or ApiExecutor()
        # F014 有限并发：默认从 settings 读取；显式传 1 即恢复串行。
        # 任何非法值（< 1）都回落到 1，避免误用。
        raw = max_concurrency if max_concurrency is not None else settings.TEST_RUN_MAX_CONCURRENCY
        self._max_concurrency = max(1, int(raw))
        # SQLAlchemy AsyncSession 不能并发 flush/commit；F014 让多个
        # case 的 HTTP 请求并发，但所有 session 操作（add/get/flush/
        # commit）必须由这把锁串行化。HTTP 请求本身在锁外，仍能并行。
        self._db_lock = asyncio.Lock()

    async def execute_run(
        self,
        *,
        run: ApiTestRun,
        env: ApiEnvironment,
        case_ids: Sequence[UUID],
    ) -> ApiTestRun:
        """Execute every case in ``case_ids`` and return the updated run.

        The run transitions ``pending → running → finished``. Counters
        are populated as each case completes. ``skipped`` is
        computed at the end as ``total - passed - failed - error``
        so callers don't need to manage it per-case.
        """
        # Mark as running before the first network call so a reader
        # polling the run endpoint sees the status change immediately.
        run.status = "running"
        run.started_at = run.started_at or datetime.now(timezone.utc)
        run.total = len(case_ids)
        async with self._db_lock:
            await self.run_repo.update(run)
            await self.session.commit()

        # F014 有限并发：用 Semaphore 控制同时在飞的 _execute_single。
        # Semaphore(1) 等价于原串行行为，Semaphore(N) 最多允许 N 个并发。
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def _bounded(case_id: UUID) -> Optional[ApiTestResult]:
            """Acquire the semaphore, then run a single case.

            Returns ``None`` for the "case disappeared" path so the
            caller can skip counting it. Catches every exception so a
            single bad case never aborts the whole gather().
            """
            async with semaphore:
                # 读取 case 也需要 DB 锁（AsyncSession 不能并发访问）
                async with self._db_lock:
                    case = await self.session.get(ApiTestCase, case_id)
                if case is None:
                    # Case was deleted between run creation and execution —
                    # skip silently and let ``skipped`` absorb the slot.
                    logger.warning(
                        "TestRunner: case %s disappeared mid-run", case_id
                    )
                    return None
                try:
                    return await self._execute_single(run=run, env=env, case=case)
                except Exception:  # pragma: no cover - defensive net
                    # ``_execute_single`` is expected to never raise; this
                    # catch exists so a regression in the engine doesn't
                    # poison the whole run.
                    logger.exception(
                        "TestRunner: unexpected error on case %s", case_id
                    )
                    return None

        results = await asyncio.gather(
            *(_bounded(case_id) for case_id in case_ids)
        )

        passed = failed = error = 0
        for result in results:
            if result is None:
                # 已被跳过的消失 case
                continue
            if result.status == "passed":
                passed += 1
            elif result.status == "failed":
                failed += 1
            elif result.status == "error":
                error += 1
            # ``skipped`` is intentionally not handled per-case.

        run.passed = passed
        run.failed = failed
        run.error = error
        run.skipped = run.total - passed - failed - error
        run.status = "finished"
        run.finished_at = datetime.now(timezone.utc)
        async with self._db_lock:
            await self.run_repo.update(run)
            await self.session.commit()
        logger.info(
            "TestRunner: run %s finished — total=%d passed=%d failed=%d "
            "error=%d skipped=%d",
            run.id,
            run.total,
            run.passed,
            run.failed,
            run.error,
            run.skipped,
        )
        return run

    # ------------------------------------------------------------------
    # Per-case execution
    # ------------------------------------------------------------------

    async def _execute_single(
        self,
        *,
        run: ApiTestRun,
        env: ApiEnvironment,
        case: ApiTestCase,
    ) -> ApiTestResult:
        """Execute one case and persist its result row.

        Never raises — every failure mode writes an ``ApiTestResult``
        with ``status="error"`` (or ``status="failed"`` for an
        assertion failure) so the run can finish with a complete
        audit trail.
        """
        started_at = datetime.now(timezone.utc)
        # 注意：不在这里 add(result)！等所有字段都 set 好之后再 add，
        # 避免被其他 case 的 query 触发的 autoflush 提前写入半成品
        # (status="error") 到 DB。result_repo.create() 内部会做 add+flush。
        result = ApiTestResult(
            id=uuid4(),
            run_id=run.id,
            test_case_id=case.id,
            case_name=case.name,
            case_method=case.method,
            case_path=case.path,
            environment_id=env.id,
            status="pending",  # placeholder，create 之前一定会被覆盖
            started_at=started_at,
        )

        # 1. Build the variable context. MVP: env variables only.
        variables: dict[str, Any] = dict(env.variables or {})

        # 2. Substituted fields used both for the request and the
        #    ``request_snapshot`` so the report shows what was actually
        #    sent (not what was stored on the case row).
        substituted_path = substitute(case.path, variables)
        substituted_headers = {
            k: substitute(v, variables) if isinstance(v, str) else str(v)
            for k, v in (case.headers or {}).items()
        }
        substituted_query = {
            k: substitute(str(v), variables)
            for k, v in (case.query_params or {}).items()
        }

        # 3. Build the request. The builder re-substitutes env-level
        #    headers internally; we only need to feed it the raw
        #    substituted case fields above to get the final URL /
        #    body right.
        case_path = ApiTestCase(
            id=case.id,
            project_id=case.project_id,
            name=case.name,
            method=case.method,
            path=substituted_path,
            headers=substituted_headers,
            query_params=substituted_query,
            body_type=case.body_type,
            body=case.body,
            assertions=case.assertions,
            timeout_seconds=case.timeout_seconds,
            status=case.status,
            sort_order=case.sort_order,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
        try:
            built = RequestBuilder.build(env, case_path, variables)
        except Exception as exc:  # pragma: no cover - defensive
            # Request construction itself is pure-Python; if it
            # raises here something is genuinely wrong upstream.
            result.status = "error"
            result.error_code = "REQUEST_BUILD_FAILED"
            result.error_message = f"failed to build request: {exc}"
            result.request_snapshot = _request_snapshot(
                method=case.method.upper(),
                url=case.path,
                headers=substituted_headers,
                params=substituted_query,
                body=None,
                timeout=float(case.timeout_seconds or 30),
                variables_used=variables,
            )
            result.finished_at = datetime.now(timezone.utc)
            async with self._db_lock:
                await self.result_repo.create(result)
                await self.session.commit()
            logger.exception(
                "TestRunner: request build failed for case %s", case.id
            )
            return result

        # 4. Execute.
        try:
            response = await self.executor.execute(built)
        except ApiExecutionTimeoutError as exc:
            return await self._persist_error(
                result=result,
                code="API_EXECUTION_TIMEOUT",
                message=str(exc),
                built=built,
                variables_used=variables,
            )
        except ApiConnectionError as exc:
            return await self._persist_error(
                result=result,
                code="API_CONNECTION_ERROR",
                message=str(exc),
                built=built,
                variables_used=variables,
            )
        except ApiExecutionError as exc:
            return await self._persist_error(
                result=result,
                code="API_EXECUTION_ERROR",
                message=str(exc),
                built=built,
                variables_used=variables,
            )

        # 5. Assertions.
        assertion_results: list[AssertionResult] = evaluate_all(
            case.assertions, response, variables
        )
        all_passed = all(r.passed for r in assertion_results)
        result.status = "passed" if all_passed else "failed"

        # 6. Build snapshots.
        result.elapsed_ms = int(response.elapsed.total_seconds() * 1000)
        result.request_snapshot = _request_snapshot_from_built(built, variables)
        result.response_snapshot = _response_snapshot(response)
        result.assertions_snapshot = [
            _assertion_to_dict(r) for r in assertion_results
        ]
        result.finished_at = datetime.now(timezone.utc)
        async with self._db_lock:
            await self.result_repo.create(result)
            await self.session.commit()
        return result

    async def _persist_error(
        self,
        *,
        result: ApiTestResult,
        code: str,
        message: str,
        built: BuiltRequest,
        variables_used: Mapping[str, Any],
    ) -> ApiTestResult:
        """Persist an error result (timeout / connection / generic)."""
        result.status = "error"
        result.error_code = code
        result.error_message = message
        result.request_snapshot = _request_snapshot_from_built(
            built, variables_used
        )
        result.response_snapshot = None
        result.assertions_snapshot = None
        result.elapsed_ms = None
        result.finished_at = datetime.now(timezone.utc)
        async with self._db_lock:
            await self.result_repo.create(result)
            await self.session.commit()
        return result


# ---------------------------------------------------------------------------
# Snapshot builders
# ---------------------------------------------------------------------------


def _sanitize_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Drop sensitive headers (``Authorization`` / ``Cookie`` / …).

    Matching is case-insensitive — HTTP header names are.
    """
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in _SENSITIVE_HEADERS
    }


def _truncate_body(body: str) -> tuple[str, bool]:
    """Truncate ``body`` to ``_MAX_RESPONSE_BODY_BYTES`` if needed.

    Returns ``(text, was_truncated)``. ``was_truncated=True`` means
    the report should display a "+N bytes hidden" indicator.
    """
    encoded = body.encode("utf-8", errors="replace")
    if len(encoded) <= _MAX_RESPONSE_BODY_BYTES:
        return body, False
    truncated = encoded[:_MAX_RESPONSE_BODY_BYTES].decode(
        "utf-8", errors="replace"
    )
    return truncated, True


def _request_snapshot(
    *,
    method: str,
    url: str,
    headers: Mapping[str, str],
    params: Mapping[str, str],
    body: Any,
    timeout: float,
    variables_used: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "method": method,
        "url": url,
        "headers": _sanitize_headers(headers),
        "params": dict(params),
        "body": body,
        "timeout": timeout,
        "variables_used": dict(variables_used),
    }


def _request_snapshot_from_built(
    built: BuiltRequest,
    variables_used: Mapping[str, Any],
) -> dict[str, Any]:
    body = (
        built.body_kwargs.get("json")
        or built.body_kwargs.get("data")
        or built.body_kwargs.get("content")
    )
    return _request_snapshot(
        method=built.method,
        url=built.url,
        headers=built.headers,
        params=built.params,
        body=body,
        timeout=built.timeout,
        variables_used=variables_used,
    )


def _response_snapshot(response: Any) -> dict[str, Any]:
    body_text: str = response.text or ""
    body, was_truncated = _truncate_body(body_text)
    return {
        "status_code": response.status_code,
        "headers": _sanitize_headers(dict(response.headers)),
        "body": body,
        "body_truncated": was_truncated,
        "elapsed_ms": int(response.elapsed.total_seconds() * 1000),
    }


def _assertion_to_dict(r: AssertionResult) -> dict[str, Any]:
    return {
        "type": r.type,
        "operator": r.operator,
        "passed": r.passed,
        "actual": r.actual,
        "expected": r.expected,
        "message": r.message,
        "path": r.path,
        "header_name": r.header_name,
    }


# Re-export so callers can ``from app.domain.test_engine.runner import
# _SENSITIVE_HEADERS`` if they ever need to extend the blocklist.
__all__ = [
    "TestRunner",
    "_SENSITIVE_HEADERS",
    "_MAX_RESPONSE_BODY_BYTES",
]


# ---------------------------------------------------------------------------
# Suite-scoped case-id lookup (used by the service layer).
# ---------------------------------------------------------------------------


async def list_case_ids_for_suite(
    session: AsyncSession, suite_id: UUID
) -> list[UUID]:
    """Return the case IDs attached to a suite, in suite-defined order.

    Uses ``ApiSuiteCase.order`` so the test run executes cases in the
    same order the user arranged them in the UI (F006 §3.6).
    """
    from sqlalchemy import select

    stmt = (
        select(ApiSuiteCase.test_case_id)
        .where(ApiSuiteCase.suite_id == suite_id)
        .order_by(ApiSuiteCase.order.asc(), ApiSuiteCase.created_at.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)