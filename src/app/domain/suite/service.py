"""Business logic for F006 suite management."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    ProjectNotFoundException,
    SuiteNotFoundException,
    TestCaseNotFoundException,
)
from app.domain.project.service import ProjectService
from app.domain.suite.model import ApiSuite, ApiSuiteCase
from app.domain.suite.repository import SuiteRepository
from app.domain.suite.schema import (
    SuiteCaseResponse,
    SuiteCasesBulkCreate,
    SuiteCasesBulkResponse,
    SuiteCasesReorderRequest,
    SuiteCreateRequest,
    SuiteDetailResponse,
    SuiteListResponse,
    SuiteResponse,
    SuiteUpdateRequest,
)
from app.domain.user.model import User

logger = logging.getLogger(__name__)


def _audit(event: str, **fields: object) -> None:
    """Emit one structured, secret-free suite audit event."""
    logger.info("suite.audit %s", {"event": event, **fields})


class SuiteService:
    """Enforce project scope, uniqueness, case existence and ordering."""

    def __init__(self, session: AsyncSession):
        self.repository = SuiteRepository(session)
        self.project_service = ProjectService(session)
        self.session = session

    async def _load_project_for_user(
        self,
        project_id: UUID,
        *,
        current_user: User,
        for_modify: bool,
    ) -> None:
        try:
            project = await self.project_service.get_project(
                project_id, current_user=current_user
            )
        except ProjectNotFoundException as exc:
            raise ProjectNotFoundException() from exc

        if for_modify and not (
            current_user.is_superuser or project.owner_id == current_user.id
        ):
            raise ForbiddenException(
                "Only a project member may modify suites in this project"
            )

    async def _load_suite_for_user(
        self, suite_id: UUID, *, current_user: User, for_modify: bool
    ) -> ApiSuite:
        suite = await self.repository.get_by_id(suite_id)
        if suite is None:
            raise SuiteNotFoundException()
        await self._load_project_for_user(
            suite.project_id,
            current_user=current_user,
            for_modify=for_modify,
        )
        return suite

    async def create_suite(
        self,
        project_id: UUID,
        request: SuiteCreateRequest,
        *,
        current_user: User,
    ) -> SuiteResponse:
        await self._load_project_for_user(
            project_id, current_user=current_user, for_modify=True
        )
        if await self.repository.get_by_project_and_name(
            project_id=project_id, name=request.name
        ):
            raise self._name_conflict(request.name)

        suite = ApiSuite(
            project_id=project_id,
            name=request.name,
            description=request.description,
            sort_order=await self.repository.next_sort_order_in_project(project_id),
        )
        try:
            await self.repository.create(suite)
            await self.session.commit()
        except IntegrityError as exc:
            # The database constraint closes the race between the pre-check and
            # INSERT, preserving the documented 409 under concurrent requests.
            await self.session.rollback()
            raise self._name_conflict(request.name) from exc

        _audit(
            "create",
            suite_id=str(suite.id),
            project_id=str(project_id),
            actor_id=str(current_user.id),
        )
        return SuiteResponse.model_validate(suite)

    async def list_suites(
        self,
        project_id: UUID,
        *,
        current_user: User,
        search: Optional[str] = None,
    ) -> SuiteListResponse:
        await self._load_project_for_user(
            project_id, current_user=current_user, for_modify=False
        )
        items, total = await self.repository.list_by_project(
            project_id=project_id, search=search
        )
        return SuiteListResponse(
            items=[SuiteResponse.model_validate(item) for item in items],
            total=total,
        )

    async def get_suite(self, suite_id: UUID, *, current_user: User) -> ApiSuite:
        """Return the ORM suite for compatibility with existing routers/tests."""
        return await self._load_suite_for_user(
            suite_id, current_user=current_user, for_modify=False
        )

    async def get_suite_detail(
        self, suite_id: UUID, *, current_user: User
    ) -> SuiteDetailResponse:
        suite = await self._load_suite_for_user(
            suite_id, current_user=current_user, for_modify=False
        )
        rows = await self.repository.list_cases_by_suite(suite_id)
        base = SuiteResponse.model_validate(suite)
        return SuiteDetailResponse(
            **base.model_dump(),
            cases=[SuiteCaseResponse.model_validate(row) for row in rows],
        )

    async def update_suite(
        self,
        suite_id: UUID,
        request: SuiteUpdateRequest,
        *,
        current_user: User,
    ) -> SuiteResponse:
        suite = await self._load_suite_for_user(
            suite_id, current_user=current_user, for_modify=True
        )
        if request.name is not None and request.name != suite.name:
            clash = await self.repository.get_by_project_and_name(
                project_id=suite.project_id, name=request.name
            )
            if clash is not None and clash.id != suite.id:
                raise self._name_conflict(request.name)
            suite.name = request.name
        if "description" in request.model_fields_set:
            suite.description = request.description

        try:
            await self.repository.update(suite)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise self._name_conflict(request.name or suite.name) from exc
        return SuiteResponse.model_validate(suite)

    async def delete_suite(self, suite_id: UUID, *, current_user: User) -> None:
        suite = await self._load_suite_for_user(
            suite_id, current_user=current_user, for_modify=True
        )
        project_id = suite.project_id
        # Explicit cleanup makes the invariant independent of whether a test
        # database enabled SQLite's opt-in foreign-key pragma. Production still
        # has ON DELETE CASCADE as a second line of defence.
        await self.repository.clear_cases(suite_id)
        await self.repository.delete(suite)
        await self.session.commit()
        _audit(
            "delete",
            suite_id=str(suite_id),
            project_id=str(project_id),
            actor_id=str(current_user.id),
        )

    async def bulk_add_cases(
        self,
        suite_id: UUID,
        request: SuiteCasesBulkCreate,
        *,
        current_user: User,
    ) -> SuiteCasesBulkResponse:
        suite = await self._load_suite_for_user(
            suite_id, current_user=current_user, for_modify=True
        )
        ordered_unique = list(dict.fromkeys(request.test_case_ids))

        valid_ids = await self.repository.find_project_test_case_ids(
            project_id=suite.project_id,
            test_case_ids=ordered_unique,
        )
        missing = [case_id for case_id in ordered_unique if case_id not in valid_ids]
        if missing:
            raise TestCaseNotFoundException(
                details={"test_case_ids": [str(case_id) for case_id in missing]}
            )

        present = await self.repository.find_existing_test_case_ids(
            suite_id=suite_id,
            test_case_ids=ordered_unique,
        )
        next_order = await self.repository.next_case_order(suite_id)
        added: list[ApiSuiteCase] = []
        for case_id in ordered_unique:
            if case_id in present:
                continue
            row = await self.repository.insert_case(
                suite_id=suite_id,
                test_case_id=case_id,
                order=next_order + len(added),
            )
            if row is None:
                # A concurrent request won the unique-key race. Duplicate adds
                # remain successful/idempotent rather than becoming a 409.
                present.add(case_id)
            else:
                added.append(row)
        await self.session.commit()

        already_present = [case_id for case_id in ordered_unique if case_id in present]
        return SuiteCasesBulkResponse(
            added=[SuiteCaseResponse.model_validate(row) for row in added],
            already_present=already_present,
        )

    async def list_suite_cases(
        self, suite_id: UUID, *, current_user: User
    ) -> list[SuiteCaseResponse]:
        await self._load_suite_for_user(
            suite_id, current_user=current_user, for_modify=False
        )
        rows = await self.repository.list_cases_by_suite(suite_id)
        return [SuiteCaseResponse.model_validate(row) for row in rows]

    async def remove_case(
        self,
        suite_id: UUID,
        test_case_id: UUID,
        *,
        current_user: User,
    ) -> None:
        await self._load_suite_for_user(
            suite_id, current_user=current_user, for_modify=True
        )
        await self.repository.delete_case(suite_id=suite_id, test_case_id=test_case_id)
        # Keep order values dense after removal.
        rows = await self.repository.list_cases_by_suite(suite_id)
        for order, row in enumerate(rows):
            row.order = order
        await self.session.commit()

    async def reorder_cases(
        self,
        suite_id: UUID,
        request: SuiteCasesReorderRequest,
        *,
        current_user: User,
    ) -> list[SuiteCaseResponse]:
        await self._load_suite_for_user(
            suite_id, current_user=current_user, for_modify=True
        )
        requested = request.ordered_test_case_ids
        current = await self.repository.list_cases_by_suite(suite_id)
        current_ids = {row.test_case_id for row in current}
        requested_ids = set(requested)
        if requested_ids != current_ids or len(requested) != len(current):
            missing_from_suite = [
                str(case_id) for case_id in requested if case_id not in current_ids
            ]
            if missing_from_suite:
                raise TestCaseNotFoundException(
                    message="One or more test cases are not in this suite",
                    details={"test_case_ids": missing_from_suite},
                )
            raise BadRequestException(
                "Reorder request must include every case in the suite exactly once"
            )

        rows = await self.repository.replace_case_order(
            suite_id=suite_id,
            ordered_test_case_ids=requested,
        )
        await self.session.commit()
        return [SuiteCaseResponse.model_validate(row) for row in rows]

    @staticmethod
    def _name_conflict(name: str) -> ConflictException:
        return ConflictException(
            message=f"Suite name '{name}' already exists in this project",
            details={"code": "SUITE_NAME_TAKEN"},
        )
