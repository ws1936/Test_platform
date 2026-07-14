"""Business logic for F010 test runs.

Owns:

* Project / suite / case / environment authorization (delegates to
  :class:`ProjectService` for the canonical owner-vs-superuser check).
* Mapping ``(scope, scope_id)`` → a concrete list of ``test_case_id``s.
* Creating the ``ApiTestRun`` row, hand-off to :class:`TestRunner`, and
  serialization of the final state.
* Read-only endpoints (list / get) used by the F011 report layer.

Errors raised here map to the 30xxx / 32xxx business codes in
``docs/03-api/ERROR_CODE.md`` §5:

* ``SuiteNotFoundException`` / ``TestCaseNotFoundException`` /
  ``EnvironmentNotFoundException``  → 30xxx
* ``BadRequestException``              → 400 (empty scope)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
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
    RunScope,
    TestResultListResponse,
    TestResultResponse,
    TestRunCreateRequest,
    TestRunListResponse,
    TestRunResponse,
)
from app.domain.user.model import User


logger = logging.getLogger(__name__)


class TestRunService:
    """Orchestrates test-run creation and read access for F010."""

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
    # Create + execute
    # ------------------------------------------------------------------

    async def create_run(
        self,
        project_id: UUID,
        request: TestRunCreateRequest,
        *,
        current_user: User,
    ) -> TestRunResponse:
        """Create + execute a run synchronously.

        The flow:

        1. Authorize the project (owner / superuser for mutation).
        2. Validate environment belongs to the same project.
        3. Resolve ``(scope, scope_id)`` → case IDs.
        4. Persist a ``pending`` run row.
        5. Hand off to :class:`TestRunner.execute_run`.
        6. Return the freshly-completed run.
        """
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
        return TestRunResponse.model_validate(updated)

    async def run_test_case(
        self,
        case_id: UUID,
        environment_id: UUID,
        *,
        current_user: User,
        name: Optional[str] = None,
    ) -> TestRunResponse:
        """Convenience entry: execute a single case as a 1-case run.

        Mirrors the API_GUIDE §3.7 ``POST /test-cases/{case_id}/run``
        endpoint. Internally it constructs a ``scope="case"`` run with
        a single case ID so the rest of the execution pipeline stays
        uniform.
        """
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
        return TestRunResponse.model_validate(updated)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_run(
        self, run_id: UUID, *, current_user: User
    ) -> ApiTestRun:
        run = await self.run_repo.get_by_id(run_id)
        if run is None:
            raise TestRunNotFoundException()
        await self._load_project_for_user(
            run.project_id, current_user=current_user, for_modify=False
        )
        return run

    async def list_project_runs(
        self,
        project_id: UUID,
        *,
        current_user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> TestRunListResponse:
        await self._load_project_for_user(
            project_id, current_user=current_user, for_modify=False
        )
        items, total = await self.run_repo.list_by_project(
            project_id=project_id, limit=limit, offset=offset
        )
        return TestRunListResponse(
            items=[TestRunResponse.model_validate(r) for r in items],
            total=total,
        )

    async def list_run_results(
        self, run_id: UUID, *, current_user: User
    ) -> TestResultListResponse:
        run = await self.get_run(run_id, current_user=current_user)
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
        await self.get_run(result.run_id, current_user=current_user)
        return result