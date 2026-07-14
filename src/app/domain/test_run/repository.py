"""SQLAlchemy repositories for F010 test runs and test results.

Thin wrappers around SQLAlchemy; the service layer owns business
rules (authorization, scope resolution, run orchestration). Mirrors
the style of :class:`app.domain.suite.repository.SuiteRepository`.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.test_run.model import ApiTestResult, ApiTestRun


class TestRunRepository:
    """Persistence operations for :class:`ApiTestRun`."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, run_id: UUID) -> Optional[ApiTestRun]:
        result = await self.session.execute(
            select(ApiTestRun).where(ApiTestRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def create(self, run: ApiTestRun) -> ApiTestRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update(self, run: ApiTestRun) -> ApiTestRun:
        """Flush pending changes and refresh server-side values."""
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def list_by_project(
        self,
        *,
        project_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> tuple[list[ApiTestRun], int]:
        """Return ``(items, total)`` for a project, newest first.

        ``total`` is computed *without* pagination so the UI can
        render an accurate count. Ordering is by ``created_at DESC``
        so the most recent run is on top.

        F011 added the optional ``status`` filter so the history
        view can show only the failed runs (or any other status).
        The total still reflects the *filtered* set.
        """
        conditions = [ApiTestRun.project_id == project_id]
        if status is not None:
            conditions.append(ApiTestRun.status == status)

        total_stmt = (
            select(func.count())
            .select_from(ApiTestRun)
            .where(*conditions)
        )
        total = (await self.session.execute(total_stmt)).scalar_one()

        rows_stmt = (
            select(ApiTestRun)
            .where(*conditions)
            .order_by(ApiTestRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(rows_stmt)).scalars().all()
        return list(rows), int(total)


class TestResultRepository:
    """Persistence operations for :class:`ApiTestResult`."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, result_id: UUID) -> Optional[ApiTestResult]:
        result = await self.session.execute(
            select(ApiTestResult).where(ApiTestResult.id == result_id)
        )
        return result.scalar_one_or_none()

    async def create(self, result: ApiTestResult) -> ApiTestResult:
        self.session.add(result)
        await self.session.flush()
        await self.session.refresh(result)
        return result

    async def list_by_run(self, run_id: UUID) -> list[ApiTestResult]:
        """Return every result for a run, in insertion order.

        ``created_at ASC`` keeps the result list in the same order
        the cases were executed, which matches the suite / project
        ordering the user sees in the UI.
        """
        rows_stmt = (
            select(ApiTestResult)
            .where(ApiTestResult.run_id == run_id)
            .order_by(ApiTestResult.created_at.asc())
        )
        rows = (await self.session.execute(rows_stmt)).scalars().all()
        return list(rows)