"""SQLAlchemy repository for F006 suites and ordered case associations."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.suite.model import ApiSuite, ApiSuiteCase
from app.domain.test_case.model import ApiTestCase


class SuiteRepository:
    """Persistence operations; authorization and invariants live in the service."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, suite_id: UUID) -> Optional[ApiSuite]:
        result = await self.session.execute(
            select(ApiSuite).where(ApiSuite.id == suite_id)
        )
        return result.scalar_one_or_none()

    async def get_by_project_and_name(
        self, *, project_id: UUID, name: str
    ) -> Optional[ApiSuite]:
        result = await self.session.execute(
            select(ApiSuite).where(
                ApiSuite.project_id == project_id,
                ApiSuite.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def next_sort_order_in_project(self, project_id: UUID) -> int:
        stmt = select(func.coalesce(func.max(ApiSuite.sort_order), -1)).where(
            ApiSuite.project_id == project_id
        )
        return int((await self.session.execute(stmt)).scalar_one()) + 1

    async def create(self, suite: ApiSuite) -> ApiSuite:
        self.session.add(suite)
        await self.session.flush()
        await self.session.refresh(suite)
        return suite

    async def update(self, suite: ApiSuite) -> ApiSuite:
        await self.session.flush()
        await self.session.refresh(suite)
        return suite

    async def delete(self, suite: ApiSuite) -> None:
        await self.session.delete(suite)
        await self.session.flush()

    async def list_by_project(
        self, *, project_id: UUID, search: Optional[str] = None
    ) -> tuple[list[ApiSuite], int]:
        conditions = [ApiSuite.project_id == project_id]
        if search:
            conditions.append(ApiSuite.name.ilike(f"%{search}%"))

        total_stmt = select(func.count()).select_from(ApiSuite).where(*conditions)
        total = (await self.session.execute(total_stmt)).scalar_one()
        rows_stmt = (
            select(ApiSuite)
            .where(*conditions)
            .order_by(ApiSuite.sort_order.asc(), ApiSuite.created_at.asc())
        )
        rows = (await self.session.execute(rows_stmt)).scalars().all()
        return list(rows), int(total)

    async def list_cases_by_suite(self, suite_id: UUID) -> list[ApiSuiteCase]:
        result = await self.session.execute(
            select(ApiSuiteCase)
            .where(ApiSuiteCase.suite_id == suite_id)
            .order_by(ApiSuiteCase.order.asc(), ApiSuiteCase.created_at.asc())
        )
        return list(result.scalars().all())

    async def find_existing_test_case_ids(
        self, *, suite_id: UUID, test_case_ids: list[UUID]
    ) -> set[UUID]:
        if not test_case_ids:
            return set()
        result = await self.session.execute(
            select(ApiSuiteCase.test_case_id).where(
                ApiSuiteCase.suite_id == suite_id,
                ApiSuiteCase.test_case_id.in_(test_case_ids),
            )
        )
        return set(result.scalars().all())

    async def find_project_test_case_ids(
        self, *, project_id: UUID, test_case_ids: list[UUID]
    ) -> set[UUID]:
        """Return requested case IDs that exist in the suite's project."""
        if not test_case_ids:
            return set()
        result = await self.session.execute(
            select(ApiTestCase.id).where(
                ApiTestCase.project_id == project_id,
                ApiTestCase.id.in_(test_case_ids),
            )
        )
        return set(result.scalars().all())

    async def next_case_order(self, suite_id: UUID) -> int:
        stmt = select(func.coalesce(func.max(ApiSuiteCase.order), -1)).where(
            ApiSuiteCase.suite_id == suite_id
        )
        return int((await self.session.execute(stmt)).scalar_one()) + 1

    async def next_case_sort_order(self, suite_id: UUID) -> int:
        """Compatibility wrapper for the previous repository API."""
        return await self.next_case_order(suite_id)

    async def insert_case(
        self,
        *,
        suite_id: UUID,
        test_case_id: UUID,
        order: Optional[int] = None,
        sort_order: Optional[int] = None,
    ) -> Optional[ApiSuiteCase]:
        """Insert one association without rolling back the outer transaction.

        A savepoint contains a race-triggered uniqueness violation.  Calling
        ``session.rollback()`` here would otherwise discard all rows inserted
        earlier in the same bulk request.
        """
        resolved_order = order if order is not None else sort_order
        if resolved_order is None:
            raise ValueError("order is required")
        row = ApiSuiteCase(
            suite_id=suite_id,
            test_case_id=test_case_id,
            order=resolved_order,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(row)
                await self.session.flush()
        except IntegrityError:
            return None
        await self.session.refresh(row)
        return row

    async def replace_case_order(
        self, *, suite_id: UUID, ordered_test_case_ids: list[UUID]
    ) -> list[ApiSuiteCase]:
        """Apply a complete dense order to the suite's current associations."""
        rows = await self.list_cases_by_suite(suite_id)
        by_id = {row.test_case_id: row for row in rows}
        for order, test_case_id in enumerate(ordered_test_case_ids):
            by_id[test_case_id].order = order
        await self.session.flush()
        # ``onupdate=func.now()`` expires updated_at on SQLite. Refresh each
        # row before the service builds Pydantic responses so serialization
        # never attempts async IO outside SQLAlchemy's greenlet.
        for row in by_id.values():
            await self.session.refresh(row)
        return [by_id[test_case_id] for test_case_id in ordered_test_case_ids]

    async def delete_case(self, *, suite_id: UUID, test_case_id: UUID) -> int:
        result = await self.session.execute(
            delete(ApiSuiteCase).where(
                ApiSuiteCase.suite_id == suite_id,
                ApiSuiteCase.test_case_id == test_case_id,
            )
        )
        return int(result.rowcount or 0)

    async def clear_cases(self, suite_id: UUID) -> int:
        result = await self.session.execute(
            delete(ApiSuiteCase).where(ApiSuiteCase.suite_id == suite_id)
        )
        return int(result.rowcount or 0)
