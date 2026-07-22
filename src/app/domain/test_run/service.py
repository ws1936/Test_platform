"""Business logic for F010 test runs + F011 report aggregations.

Owns:

* Project / suite / case / environment authorization (delegates to
  :class:`ProjectService` for the canonical owner-vs-superuser check).
* Mapping ``(scope, scope_id)`` → a concrete list of ``test_case_id``s.
* Creating the ``ApiTestRun`` row, hand-off to :class:`TestRunner`, and
  serialization of the final state.
* F010 read endpoints (list / get) used by the F011 report layer.
* F011 aggregations:
  - ``summarize_run(run_id)`` — single-run roll-up (counters +
    ``pass_rate`` + ``elapsed_seconds``).
  - ``summarize_project_runs(project_id)`` — project-level roll-up
    (sum of every result + recent runs).
  - ``list_run_failures(run_id)`` — flatten every
    ``assertions_snapshot`` to one item per failed assertion so the
    report UI doesn't have to re-parse JSON.

Errors raised here map to the 30xxx / 32xxx business codes in
``docs/03-api/ERROR_CODE.md`` §5:

* ``SuiteNotFoundException`` / ``TestCaseNotFoundException`` /
  ``EnvironmentNotFoundException``  → 30xxx
* ``BadRequestException``              → 400 (empty scope / bad status filter)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    BadRequestException,
    EnvironmentNotFoundException,
    ForbiddenException,
    ProjectNotFoundException,
    SuiteNotFoundException,
    TestCaseNotFoundException,
    TestResultNotFoundException,
    TestRunNotFoundException,
)
from app.domain.environment.model import ApiEnvironment
from app.domain.environment.repository import EnvironmentRepository
from app.domain.project.service import ProjectService
from app.domain.suite.model import ApiSuiteCase
from app.domain.suite.repository import SuiteRepository
from app.domain.test_case.model import ApiTestCase
from app.domain.test_case.repository import TestCaseRepository
from app.domain.test_engine.runner import TestRunner, list_case_ids_for_suite
from app.domain.test_run.model import ApiTestResult, ApiTestRun
from app.domain.test_run.repository import TestResultRepository, TestRunRepository
from app.domain.test_run.schema import (
    ProjectRunsSummaryResponse,
    RunScope,
    RunStatus,
    TestResultFailureItem,
    TestResultFailureListResponse,
    TestResultListResponse,
    TestResultResponse,
    TestRunCreateRequest,
    TestRunListResponse,
    TestRunResponse,
    TestRunSummaryResponse,
)
from app.domain.test_run.exporter import export_run as _export_run_impl

from app.domain.user.model import User


logger = logging.getLogger(__name__)


# === F011 helpers ==========================================================


# Statuses that count as "failure" for the F011 failure endpoint.
# ``error`` is in here on purpose — the brief explicitly recommends
# surfacing connection / timeout errors alongside assertion failures
# so the report UI shows *why* a batch broke.
_FAILURE_STATUSES: frozenset[str] = frozenset({"failed", "error"})


def _pass_rate(passed: int, total: int) -> Optional[float]:
    """Return ``passed / total`` rounded to 4 decimals, or ``None``.

    ``None`` when ``total == 0`` so the UI never displays a NaN or
    a misleading ``0.0`` for an empty run.
    """
    if total <= 0:
        return None
    return round(passed / total, 4)


def _elapsed_seconds(
    started_at: Optional[datetime],
    finished_at: Optional[datetime],
) -> Optional[float]:
    """``(finished_at - started_at).total_seconds()`` or ``None``."""
    if started_at is None or finished_at is None:
        return None
    delta = finished_at - started_at
    return round(delta.total_seconds(), 3)


def _decorate_run_response(run: ApiTestRun, response: TestRunResponse) -> TestRunResponse:
    """Mutate ``response`` in place to attach the F011 computed fields.

    The F010 service code constructs ``TestRunResponse`` directly from
    the ORM row (so it doesn't see derived attributes like
    ``pass_rate``); this helper fills those two fields in *after*
    construction so the wire format carries them consistently across
    every endpoint.
    """
    response.pass_rate = _pass_rate(response.passed, response.total)
    response.elapsed_seconds = _elapsed_seconds(
        response.started_at, response.finished_at
    )
    return response


class TestRunService:
    """Orchestrates test-run creation + F010 reads + F011 aggregations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.run_repo = TestRunRepository(session)
        self.result_repo = TestResultRepository(session)
        self.project_service = ProjectService(session)
        self.env_repo = EnvironmentRepository(session)
        self.suite_repo = SuiteRepository(session)
        self.case_repo = TestCaseRepository(session)

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    async def _load_project_for_user(
        self,
        project_id: UUID,
        *,
        current_user: User,
        for_modify: bool,
    ) -> None:
        """Reuse the canonical owner / superuser check from F004."""
        try:
            project = await self.project_service.get_project(
                project_id, current_user=current_user
            )
        except ProjectNotFoundException:
            raise ProjectNotFoundException()

        if for_modify and not (
            current_user.is_superuser or project.owner_id == current_user.id
        ):
            raise ForbiddenException(
                "Only the project owner or an admin may trigger runs"
            )

    # ------------------------------------------------------------------
    # Scope resolution
    # ------------------------------------------------------------------

    async def _resolve_case_ids(
        self,
        *,
        scope: RunScope,
        scope_id: UUID,
        project_id: UUID,
    ) -> list[UUID]:
        """Translate ``(scope, scope_id)`` → ordered list of case IDs.

        Empty result sets raise :class:`BadRequestException` — better
        to fail fast at the API edge than to persist an empty run that
        the report layer has nothing to show.
        """
        if scope == "case":
            case = await self.case_repo.get_by_id(scope_id)
            if case is None or case.project_id != project_id:
                raise TestCaseNotFoundException()
            if case.status != 1:
                raise BadRequestException("Test case is disabled")
            return [case.id]

        if scope == "collection":
            suite = await self.suite_repo.get_by_id(scope_id)
            if suite is None or suite.project_id != project_id:
                raise SuiteNotFoundException()
            suite_case_ids = await list_case_ids_for_suite(
                self.session, suite.id
            )
            if not suite_case_ids:
                raise BadRequestException(
                    "Suite has no attached test cases"
                )
            return suite_case_ids

        if scope == "project":
            items, _ = await self.case_repo.list_by_project(
                project_id=project_id
            )
            # ``status`` is an int column (1 = enabled, 0 = disabled).
            # ``enabled`` is the public-API name (see F007); the ORM
            # row carries the int directly.
            enabled_ids = [c.id for c in items if c.status == 1]
            if not enabled_ids:
                raise BadRequestException(
                    "Project has no enabled test cases"
                )
            return enabled_ids

        # ``RunScope`` is a Literal — defensive unreachable branch.
        raise BadRequestException(f"unknown scope: {scope!r}")

    @staticmethod
    def _generate_name(provided: Optional[str]) -> str:
        if provided:
            return provided
        return f"Run @ {datetime.now(timezone.utc).isoformat()}"

    # ------------------------------------------------------------------
    # Create + execute (F010)
    # ------------------------------------------------------------------

    async def create_run(
        self,
        project_id: UUID,
        request: TestRunCreateRequest,
        *,
        current_user: User,
    ) -> TestRunResponse:
        """Create + execute a run synchronously."""
        await self._load_project_for_user(
            project_id, current_user=current_user, for_modify=True
        )

        env = await self.env_repo.get_by_id(request.environment_id)
        if env is None or env.project_id != project_id:
            raise EnvironmentNotFoundException()

        case_ids = await self._resolve_case_ids(
            scope=request.scope,
            scope_id=request.scope_id,
            project_id=project_id,
        )

        run = ApiTestRun(
            id=uuid4(),
            project_id=project_id,
            environment_id=env.id,
            name=self._generate_name(request.name),
            scope=request.scope,
            status="pending",
            triggered_by=current_user.id,
            total=len(case_ids),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await self.run_repo.create(run)
        await self.session.commit()

        runner = TestRunner(self.session)
        updated = await runner.execute_run(run=run, env=env, case_ids=case_ids)
        response = TestRunResponse.model_validate(updated)
        return _decorate_run_response(updated, response)

    async def run_test_case(
        self,
        case_id: UUID,
        environment_id: UUID,
        *,
        current_user: User,
        name: Optional[str] = None,
    ) -> TestRunResponse:
        """Convenience entry: execute a single case as a 1-case run."""
        case = await self.case_repo.get_by_id(case_id)
        if case is None:
            raise TestCaseNotFoundException()
        await self._load_project_for_user(
            case.project_id, current_user=current_user, for_modify=True
        )

        env = await self.env_repo.get_by_id(environment_id)
        if env is None or env.project_id != case.project_id:
            raise EnvironmentNotFoundException()

        if case.status != 1:
            raise BadRequestException("Test case is disabled")

        generated = self._generate_name(name) + f" — {case.name}"
        run = ApiTestRun(
            id=uuid4(),
            project_id=case.project_id,
            environment_id=env.id,
            name=generated,
            scope="case",
            status="pending",
            triggered_by=current_user.id,
            total=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await self.run_repo.create(run)
        await self.session.commit()

        runner = TestRunner(self.session)
        updated = await runner.execute_run(
            run=run, env=env, case_ids=[case.id]
        )
        response = TestRunResponse.model_validate(updated)
        return _decorate_run_response(updated, response)

    # ------------------------------------------------------------------
    # F010 Reads
    # ------------------------------------------------------------------

    async def get_run(
        self, run_id: UUID, *, current_user: User
    ) -> TestRunResponse:
        """Return the F010 run response (now F011-decorated)."""
        run = await self._load_run_orm(run_id, current_user=current_user)
        response = TestRunResponse.model_validate(run)
        return _decorate_run_response(run, response)

    async def list_project_runs(
        self,
        project_id: UUID,
        *,
        current_user: User,
        limit: int = 50,
        offset: int = 0,
        status: Optional[RunStatus] = None,
    ) -> TestRunListResponse:
        """List runs in a project, newest first.

        F011 adds an optional ``status`` filter so the history view
        can show only the "failed" runs (or any other status).
        Passing an unknown status is a 400 (``BadRequestException``)
        rather than a silent no-op.
        """
        await self._load_project_for_user(
            project_id, current_user=current_user, for_modify=False
        )
        items, total = await self.run_repo.list_by_project(
            project_id=project_id,
            limit=limit,
            offset=offset,
            status=status,
        )
        decorated = [
            _decorate_run_response(row, TestRunResponse.model_validate(row))
            for row in items
        ]
        return TestRunListResponse(items=decorated, total=total)

    async def list_run_results(
        self, run_id: UUID, *, current_user: User
    ) -> TestResultListResponse:
        run = await self._load_run_orm(run_id, current_user=current_user)
        rows = await self.result_repo.list_by_run(run.id)
        return TestResultListResponse(
            items=[TestResultResponse.model_validate(r) for r in rows],
            total=len(rows),
        )

    async def get_result(
        self, result_id: UUID, *, current_user: User
    ) -> ApiTestResult:
        result = await self.result_repo.get_by_id(result_id)
        if result is None:
            raise TestResultNotFoundException()
        # Authorize via the parent run (one auth check covers the
        # project access path that ``get_run`` already validated).
        await self._load_run_orm(result.run_id, current_user=current_user)
        return result

    # ------------------------------------------------------------------
    # F011 Aggregations
    # ------------------------------------------------------------------

    async def summarize_run(
        self,
        run_id: UUID,
        *,
        current_user: User,
    ) -> TestRunSummaryResponse:
        """Single-run roll-up: counters + pass_rate + elapsed_seconds.

        Mirrors :class:`TestRunResponse` but with a ``run_id`` alias
        so the report UI can render this without a second lookup.
        ``pass_rate`` is ``None`` when ``total == 0``; ``elapsed_seconds``
        is ``None`` until the run has finished.
        """
        run = await self._load_run_orm(run_id, current_user=current_user)
        return TestRunSummaryResponse(
            run_id=run.id,
            name=run.name,
            scope=run.scope,
            status=run.status,
            total=run.total,
            passed=run.passed,
            failed=run.failed,
            skipped=run.skipped,
            error=run.error,
            pass_rate=_pass_rate(run.passed, run.total),
            elapsed_seconds=_elapsed_seconds(
                run.started_at, run.finished_at
            ),
            started_at=run.started_at,
            finished_at=run.finished_at,
            environment_id=run.environment_id,
        )

    async def summarize_project_runs(
        self,
        project_id: UUID,
        *,
        current_user: User,
        recent_limit: int = 10,
    ) -> ProjectRunsSummaryResponse:
        """Project-level roll-up.

        Aggregates across every run/result in the project so the
        report UI can render a single pass-rate gauge + a "recent
        N runs" list. The aggregation runs as a single SQL query
        against ``api_test_results`` joined with ``api_test_runs``
        (filtered by ``project_id``) — no Python-side iteration.
        """
        await self._load_project_for_user(
            project_id, current_user=current_user, for_modify=False
        )

        # Counters across the whole project.
        agg_stmt = (
            select(
                func.count(ApiTestResult.id),
                func.coalesce(
                    func.sum(ApiTestResult.status == "passed"), 0
                ),
                func.coalesce(
                    func.sum(ApiTestResult.status == "failed"), 0
                ),
                func.coalesce(
                    func.sum(ApiTestResult.status == "error"), 0
                ),
            )
            .join(ApiTestRun, ApiTestRun.id == ApiTestResult.run_id)
            .where(ApiTestRun.project_id == project_id)
        )
        total_cases, total_passed, total_failed, total_error = (
            await self.session.execute(agg_stmt)
        ).one()
        total_cases = int(total_cases or 0)
        total_passed = int(total_passed or 0)
        total_failed = int(total_failed or 0)
        total_error = int(total_error or 0)

        # Most recent runs (F011 brief recommends N=10).
        recent_runs, total_runs = await self.run_repo.list_by_project(
            project_id=project_id,
            limit=recent_limit,
            offset=0,
        )
        recent_summaries = [
            TestRunSummaryResponse(
                run_id=run.id,
                name=run.name,
                scope=run.scope,
                status=run.status,
                total=run.total,
                passed=run.passed,
                failed=run.failed,
                skipped=run.skipped,
                error=run.error,
                pass_rate=_pass_rate(run.passed, run.total),
                elapsed_seconds=_elapsed_seconds(
                    run.started_at, run.finished_at
                ),
                started_at=run.started_at,
                finished_at=run.finished_at,
                environment_id=run.environment_id,
            )
            for run in recent_runs
        ]

        # ``last_run_at`` is the most recent ``finished_at`` of the
        # project — useful as a "last run" timestamp on the dashboard.
        last_run_at_stmt = (
            select(func.max(ApiTestRun.finished_at))
            .where(ApiTestRun.project_id == project_id)
        )
        last_run_at = (
            await self.session.execute(last_run_at_stmt)
        ).scalar_one()
        last_run_at = (
            last_run_at if isinstance(last_run_at, datetime) else None
        )

        return ProjectRunsSummaryResponse(
            project_id=project_id,
            total_runs=int(total_runs),
            total_cases=total_cases,
            total_passed=total_passed,
            total_failed=total_failed,
            total_error=total_error,
            overall_pass_rate=_pass_rate(total_passed, total_cases),
            last_run_at=last_run_at,
            recent_runs=recent_summaries,
            recent_limit=recent_limit,
        )

    async def export_run(
        self,
        run_id: UUID,
        format: str,
        *,
        current_user: User,
    ):
        """F015 报告导出：委托给 exporter 模块。

        Returns:
            (content, media_type, filename)
        """
        if format not in ("json", "html"):
            from app.common.exceptions import BadRequestException

            raise BadRequestException(
                f"format must be 'json' or 'html', got {format!r}"
            )
        # 复用 _load_run_orm 鉴权 + 加载
        run = await self._load_run_orm(run_id, current_user=current_user)
        results = await self.result_repo.list_by_run(run.id)
        return _export_run_impl(run, results, format)

    async def list_run_failures(
        self,
        run_id: UUID,
        *,
        current_user: User,
    ) -> TestResultFailureListResponse:
        """Flatten every failed result in a run to one item per assertion.

        "Failure" here means ``status in {"failed", "error"}`` — the
        brief explicitly recommends surfacing engine errors (timeout
        / connect) alongside assertion failures. The function does
        **not** raise for empty results; an empty list is the
        success-case response (the run passed everything).
        """
        run = await self._load_run_orm(run_id, current_user=current_user)
        rows = await self.result_repo.list_by_run(run.id)

        items: list[TestResultFailureItem] = []
        for row in rows:
            if row.status not in _FAILURE_STATUSES:
                continue

            # Engine-level error → single item with no specific
            # assertion (the error was at the transport level, not
            # at any of the case's assertions).
            if row.status == "error":
                items.append(
                    TestResultFailureItem(
                        result_id=row.id,
                        run_id=row.run_id,
                        test_case_id=row.test_case_id,
                        case_name=row.case_name,
                        case_method=row.case_method,
                        case_path=row.case_path,
                        started_at=row.started_at,
                        finished_at=row.finished_at,
                        failure_index=0,
                        assertion_type="execution",
                        assertion_operator="n/a",
                        expected=None,
                        actual=None,
                        message=row.error_message or "execution error",
                        error_code=row.error_code,
                        error_message=row.error_message,
                    )
                )
                continue

            # Assertion-level failure: walk assertions_snapshot and
            # emit one item per ``passed=False`` assertion.
            assertions = row.assertions_snapshot or []
            for index, assertion in enumerate(assertions):
                if assertion.get("passed", True):
                    continue
                items.append(
                    TestResultFailureItem(
                        result_id=row.id,
                        run_id=row.run_id,
                        test_case_id=row.test_case_id,
                        case_name=row.case_name,
                        case_method=row.case_method,
                        case_path=row.case_path,
                        started_at=row.started_at,
                        finished_at=row.finished_at,
                        failure_index=index,
                        assertion_type=str(assertion.get("type", "unknown")),
                        assertion_operator=str(
                            assertion.get("operator", "unknown")
                        ),
                        expected=assertion.get("expected"),
                        actual=assertion.get("actual"),
                        message=str(
                            assertion.get(
                                "message",
                                f"{assertion.get('type', '?')} "
                                f"{assertion.get('operator', '?')} failed",
                            )
                        ),
                        error_code=None,
                        error_message=None,
                    )
                )

        return TestResultFailureListResponse(
            run_id=run.id,
            total_failures=len(items),
            items=items,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_run_orm(
        self, run_id: UUID, *, current_user: User
    ) -> ApiTestRun:
        """Load a run row, enforcing project access.

        Centralises the get-by-id + auth check that F010 / F011
        endpoints both need; raising 404 here keeps the public
        endpoints small.
        """
        run = await self.run_repo.get_by_id(run_id)
        if run is None:
            raise TestRunNotFoundException()
        await self._load_project_for_user(
            run.project_id, current_user=current_user, for_modify=False
        )
        return run
