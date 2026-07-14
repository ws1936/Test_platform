"""SQLAlchemy repository for F007 API test cases.

Thin wrapper around SQLAlchemy; the service layer owns business rules
(authorization, suite membership, response shaping). Mirrors the style
of :class:`app.domain.environment.repository.EnvironmentRepository` and
:class:`app.domain.suite.repository.SuiteRepository`.

Note
----
``api_test_cases`` already exists in the database — the table was
created in migration ``0006_api_suites`` so F006 could enforce
"referenced test-case IDs exist and belong to the same project" on
``api_suite_cases``. F007 does **not** introduce a new migration; it
simply starts using that table for its own CRUD surface.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.test_case.model import ApiTestCase


class TestCaseRepository:
    """Persistence operations for API test cases."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # === Single-row reads ===

    async def get_by_id(self, test_case_id: UUID) -> Optional[ApiTestCase]:
        """Fetch a test case by primary key, or ``None``."""
        result = await self.session.execute(
            select(ApiTestCase).where(ApiTestCase.id == test_case_id)
        )
        return result.scalar_one_or_none()

    async def find_ids_in_project(
        self, *, project_id: UUID, test_case_ids: list[UUID]
    ) -> set[UUID]:
        """Return the subset of ``test_case_ids`` that belong to ``project_id``.

        Used by the service layer to validate "these case IDs are in
        this project" without issuing N round trips. Returns an empty
        set when ``test_case_ids`` is empty so callers don't need a
        special case.
        """
        if not test_case_ids:
            return set()
        result = await self.session.execute(
            select(ApiTestCase.id).where(
                ApiTestCase.project_id == project_id,
                ApiTestCase.id.in_(test_case_ids),
            )
        )
        return set(result.scalars().all())

    # === Writes ===

    async def create(self, case: ApiTestCase) -> ApiTestCase:
        """Insert a new test case and refresh server-side defaults."""
        self.session.add(case)
        await self.session.flush()
        await self.session.refresh(case)
        return case

    async def update(self, case: ApiTestCase) -> ApiTestCase:
        """Flush pending changes and refresh server-side values."""
        await self.session.flush()
        await self.session.refresh(case)
        return case

    async def delete(self, case: ApiTestCase) -> None:
        """Hard-delete the row.

        ``api_suite_cases.test_case_id`` carries ``ON DELETE CASCADE``
        so any association rows are removed automatically; the test
        suite additionally enables ``PRAGMA foreign_keys=ON`` on the
        SQLite engine used by tests.
        """
        await self.session.delete(case)
        await self.session.flush()

    async def next_sort_order_in_project(self, project_id: UUID) -> int:
        """Return the next monotonic ``sort_order`` value for a project.

        Used as the default position of a freshly created test case so
        ``list_by_project`` returns cases in insertion order. Mirrors
        the same pattern used by :class:`SuiteRepository`.
        """
        stmt = select(func.coalesce(func.max(ApiTestCase.sort_order), -1)).where(
            ApiTestCase.project_id == project_id
        )
        return int((await self.session.execute(stmt)).scalar_one()) + 1

    # === List ===

    async def list_by_project(
        self,
        *,
        project_id: UUID,
        search: Optional[str] = None,
    ) -> tuple[list[ApiTestCase], int]:
        """List test cases of a project, optionally filtered by name.

        Returns ``(items, total)``. ``total`` is computed *after*
        applying the search filter so the UI can render an accurate
        count. ``sort_order`` is the primary ordering — a project
        with no explicit reordering keeps insertion order.

        Sorting
        -------
        * ``sort_order ASC`` — primary, so a UI that exposes drag-to-
          reorder sees the explicit user intent.
        * ``created_at ASC`` — tiebreaker so two cases with the same
          ``sort_order`` keep a stable order across requests.
        """
        conditions = [ApiTestCase.project_id == project_id]
        if search:
            conditions.append(ApiTestCase.name.ilike(f"%{search}%"))

        total_stmt = (
            select(func.count()).select_from(ApiTestCase).where(*conditions)
        )
        total = (await self.session.execute(total_stmt)).scalar_one()

        list_stmt = (
            select(ApiTestCase)
            .where(*conditions)
            .order_by(ApiTestCase.sort_order.asc(), ApiTestCase.created_at.asc())
        )
        items = list((await self.session.execute(list_stmt)).scalars().all())

        return items, int(total)