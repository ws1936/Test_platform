"""Business logic for F007 API test case management.

Business rules implemented here:

* Every operation is **scoped to a project**. The service reuses
  :class:`ProjectService` to validate project existence and the
  caller's authorization (project owner or superuser). Non-owners
  get ``403 Forbidden``; missing projects get ``404`` — the same
  split used by F004 / F005 / F006 so callers don't have to learn
  new rules per feature.
* Test cases are project-level entities; they are *attached* to a
  suite only via the existing ``api_suite_cases`` association table
  (F006). F007 does **not** require a test case to belong to any
  suite at creation time — that decision keeps F007 independent of
  the suite-assignment lifecycle and lets future Features (F008,
  F009) re-use the same model without a migration.
* The database column ``status`` (int) is mapped to ``enabled``
  (bool) on the wire; the service is the single conversion point.
* ``sort_order`` is monotonically allocated per project so a stable
  default ordering is preserved even before any explicit reorder
  is requested (consistent with :class:`SuiteService`).

Out of scope (deferred to later Features)
-----------------------------------------
* **Assertion execution** — assertions are stored verbatim;
  evaluation lives in F009 (assertion engine).
* **Variable substitution** — ``{{var}}`` placeholders are stored
  as-is; substitution lives in F008.
* **HTTP execution** — ``POST /cases/{id}/run`` lives in F010.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    ForbiddenException,
    ProjectNotFoundException,
    SuiteNotFoundException,
    TestCaseNotFoundException,
)
from app.domain.project.service import ProjectService
from app.domain.suite.model import ApiSuite
from app.domain.suite.repository import SuiteRepository
from app.domain.test_case.model import ApiTestCase
from app.domain.test_case.repository import TestCaseRepository
from app.domain.test_case.schema import (
    TestCaseCreateRequest,
    TestCaseListResponse,
    TestCaseResponse,
    TestCaseUpdateRequest,
)
from app.domain.user.model import User

logger = logging.getLogger(__name__)


def _audit(
    event: str,
    *,
    test_case_id: Optional[str] = None,
    project_id: Optional[str] = None,
    suite_id: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> None:
    """Emit a structured audit log line without leaking secrets.

    Matches the shape used by ``ProjectService._audit`` /
    ``EnvironmentService._audit`` so log lines are easy to grep across
    features.
    """
    fields: dict[str, str] = {"event": event}
    if test_case_id is not None:
        fields["test_case_id"] = test_case_id
    if project_id is not None:
        fields["project_id"] = project_id
    if suite_id is not None:
        fields["suite_id"] = suite_id
    if actor_id is not None:
        fields["actor_id"] = actor_id
    logger.info("test_case.audit %s", fields)


class TestCaseService:
    """Test case business logic for F007."""

    def __init__(self, session: AsyncSession):
        self.repository = TestCaseRepository(session)
        self.project_service = ProjectService(session)
        self.suite_repository = SuiteRepository(session)
        self.session = session

    # === Helpers ===

    async def _load_project_for_user(
        self,
        project_id: UUID,
        *,
        current_user: User,
        for_modify: bool,
    ) -> None:
        """Confirm the project exists and the caller may access it.

        Delegates to :py:meth:`ProjectService.get_project` so the same
        404-vs-403 split and "owner or superuser" rule used by F004 /
        F005 / F006 also applies to F007.

        Args:
            current_user: authenticated user (keyword-only).
            for_modify: if ``True``, an additional owner / admin
                check is applied before mutating operations.
        """
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
                "Only the project owner or an admin may modify test cases"
            )

    async def _load_suite_for_user(
        self,
        suite_id: UUID,
        *,
        current_user: User,
        for_modify: bool,
    ) -> ApiSuite:
        """Confirm the suite exists and the caller may access it.

        Used by the suite-scoped create / list endpoints. The suite
        is the URL anchor for those routes; the actual project
        ownership check happens through ``_load_project_for_user``.
        """
        suite = await self.suite_repository.get_by_id(suite_id)
        if suite is None:
            raise SuiteNotFoundException()
        await self._load_project_for_user(
            suite.project_id,
            current_user=current_user,
            for_modify=for_modify,
        )
        return suite

    @staticmethod
    def _to_response(case: ApiTestCase) -> TestCaseResponse:
        """Convert an ORM row into the public response schema.

        ``status`` (int, 1=enabled) is converted to ``enabled``
        (bool) here so the storage shape can stay portable while
        the wire format stays boolean.
        """
        return TestCaseResponse.model_validate(
            {
                "id": case.id,
                "project_id": case.project_id,
                "name": case.name,
                "method": case.method,
                "path": case.path,
                "headers": case.headers,
                "query_params": case.query_params,
                "body_type": case.body_type,
                "body": case.body,
                "assertions": case.assertions,
                "timeout_seconds": case.timeout_seconds,
                "sort_order": case.sort_order,
                "enabled": bool(case.status),
                "created_at": case.created_at,
                "updated_at": case.updated_at,
            }
        )

    # === Create ===

    async def create_test_case(
        self,
        suite_id: UUID,
        request: TestCaseCreateRequest,
        *,
        current_user: User,
    ) -> TestCaseResponse:
        """Create a new test case under the project that owns ``suite_id``.

        The suite URL segment is the API anchor for "create inside a
        suite" (API_GUIDE §3.7); the project's owner / superuser
        check rides on the suite's project. ``project_id`` is taken
        from the suite so the client cannot accidentally target a
        different project by sending one in the payload.

        Authorization: project owner or superuser.
        """
        suite = await self._load_suite_for_user(
            suite_id, current_user=current_user, for_modify=True
        )

        sort_order = await self.repository.next_sort_order_in_project(
            suite.project_id
        )
        case = ApiTestCase(
            project_id=suite.project_id,
            name=request.name,
            method=request.method,
            path=request.path,
            headers=request.headers,
            query_params=request.query_params,
            body_type=request.body_type,
            body=request.body,
            assertions=request.assertions,
            timeout_seconds=request.timeout_seconds,
            status=1 if request.enabled else 0,
            sort_order=sort_order,
        )
        case = await self.repository.create(case)
        # Attach to the suite the case was created under so the
        # suite-scoped list endpoint can find it.  ``insert_case``
        # itself tolerates a unique-key race (concurrent create +
        # bulk-add) by returning ``None`` instead of raising; we
        # simply ignore that case here because we are the inserter.
        next_order = await self.suite_repository.next_case_order(suite_id)
        await self.suite_repository.insert_case(
            suite_id=suite_id,
            test_case_id=case.id,
            order=next_order,
        )
        await self.session.commit()

        _audit(
            "create",
            test_case_id=str(case.id),
            project_id=str(suite.project_id),
            suite_id=str(suite_id),
            actor_id=str(current_user.id),
        )
        return self._to_response(case)

    # === Read ===

    async def get_test_case(
        self,
        test_case_id: UUID,
        *,
        current_user: User,
    ) -> ApiTestCase:
        """Fetch a test case by ID and verify project access.

        Authorization: project owner or superuser. Non-owners get
        ``403 Forbidden``; missing test cases get ``404``.

        Raises:
            TestCaseNotFoundException: when the test case does not
                exist.
        """
        case = await self.repository.get_by_id(test_case_id)
        if case is None:
            raise TestCaseNotFoundException()
        await self._load_project_for_user(
            case.project_id, current_user=current_user, for_modify=False
        )
        return case

    async def list_suite_cases(
        self,
        suite_id: UUID,
        *,
        current_user: User,
    ) -> list[TestCaseResponse]:
        """Return every test case currently attached to ``suite_id``.

        "Currently attached" follows ``api_suite_cases`` so the
        ordering matches what the suite's own endpoint emits — i.e.
        cases appear in the same order they would in the suite detail
        response. Free-floating test cases (not in any suite) are
        intentionally excluded; callers use :py:meth:`list_project_cases`
        for that view.
        """
        from sqlalchemy import select

        from app.domain.suite.model import ApiSuiteCase

        suite = await self._load_suite_for_user(
            suite_id, current_user=current_user, for_modify=False
        )
        del suite  # used only for the auth side-effect

        stmt = (
            select(ApiTestCase)
            .join(ApiSuiteCase, ApiSuiteCase.test_case_id == ApiTestCase.id)
            .where(ApiSuiteCase.suite_id == suite_id)
            .order_by(ApiSuiteCase.order.asc(), ApiSuiteCase.created_at.asc())
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return [self._to_response(item) for item in items]

    async def list_project_cases(
        self,
        project_id: UUID,
        *,
        current_user: User,
        search: Optional[str] = None,
    ) -> TestCaseListResponse:
        """Return every test case of a project (including free-floating ones)."""
        await self._load_project_for_user(
            project_id, current_user=current_user, for_modify=False
        )
        items, total = await self.repository.list_by_project(
            project_id=project_id, search=search
        )
        return TestCaseListResponse(
            items=[self._to_response(item) for item in items],
            total=total,
        )

    # === Update ===

    async def update_test_case(
        self,
        test_case_id: UUID,
        request: TestCaseUpdateRequest,
        *,
        current_user: User,
    ) -> TestCaseResponse:
        """Update mutable fields of a test case.

        Authorization: project owner or superuser. Only fields present
        in the payload are touched — this matches the partial-update
        convention used by F005 / F006 so a client can PATCH a single
        field without re-sending the full row.

        ``sort_order`` is intentionally not modifiable here — the
        per-project ordering is a derived state managed by the
        create path's monotonic allocator and by future reorder
        endpoints (out of scope for F007).
        """
        case = await self.repository.get_by_id(test_case_id)
        if case is None:
            raise TestCaseNotFoundException()
        await self._load_project_for_user(
            case.project_id, current_user=current_user, for_modify=True
        )

        # The set of fields that map 1:1 between the request model
        # and the ORM row. Listed explicitly so future schema drift
        # surfaces as an AttributeError at the call site instead of
        # silently passing through.
        for field in (
            "name",
            "method",
            "path",
            "headers",
            "query_params",
            "body_type",
            "body",
            "assertions",
            "timeout_seconds",
        ):
            value = getattr(request, field)
            if value is not None:
                setattr(case, field, value)

        if "enabled" in request.model_fields_set and request.enabled is not None:
            case.status = 1 if request.enabled else 0

        case = await self.repository.update(case)
        await self.session.commit()

        _audit(
            "update",
            test_case_id=str(test_case_id),
            project_id=str(case.project_id),
            actor_id=str(current_user.id),
        )
        return self._to_response(case)

    # === Delete ===

    async def delete_test_case(
        self,
        test_case_id: UUID,
        *,
        current_user: User,
    ) -> None:
        """Hard-delete a test case.

        Authorization: project owner or superuser.

        ``api_suite_cases.test_case_id`` carries
        ``ON DELETE CASCADE`` so any suite associations are removed
        automatically; we don't have to touch them here. The test
        engine additionally enables ``PRAGMA foreign_keys=ON`` on
        SQLite so the cascade actually fires (Review M-S2: don't
        rely on the production-only cascade to make the test suite
        happy).
        """
        case = await self.repository.get_by_id(test_case_id)
        if case is None:
            raise TestCaseNotFoundException()
        await self._load_project_for_user(
            case.project_id, current_user=current_user, for_modify=True
        )

        project_id = case.project_id
        await self.repository.delete(case)
        await self.session.commit()

        _audit(
            "delete",
            test_case_id=str(test_case_id),
            project_id=str(project_id),
            actor_id=str(current_user.id),
        )