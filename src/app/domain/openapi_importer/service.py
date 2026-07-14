"""F012 OpenAPI import service."""
from __future__ import annotations
import logging
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenException, ProjectNotFoundException
from app.domain.openapi_importer.exceptions import OpenApiImportConflictError
from app.domain.openapi_importer.parser import OpenApiSpecParser, ParsedSpec
from app.domain.openapi_importer.schema import (
    ImportPreviewResponse,
    ImportResponse,
    OperationPreview,
)
from app.domain.project.service import ProjectService
from app.domain.suite.repository import SuiteRepository
from app.domain.suite.service import SuiteService
from app.domain.test_case.model import ApiTestCase
from app.domain.test_case.schema import TestCaseCreateRequest
from app.domain.test_case.service import TestCaseService
from app.domain.user.model import User


logger = logging.getLogger(__name__)


class OpenApiImportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.parser = OpenApiSpecParser()
        self.project_service = ProjectService(session)
        self.suite_service = SuiteService(session)
        self.test_case_service = TestCaseService(session)
        # Cache preview responses for the
        # ``POST 同一端点 ?dry_run=false`` flow without re-fetching
        # the spec from the network.
        self._preview_cache: dict[str, ParsedSpec] = {}

    async def preview(
        self,
        *,
        project_id: UUID,
        suite_id: UUID,
        source_url: Optional[str],
        source_content: Optional[dict],
        tags: Optional[list[str]] = None,
        on_conflict: str = "skip",
        current_user: User,
    ) -> ImportPreviewResponse:
        await self._load_project_suite(project_id, suite_id, current_user)
        spec = (
            self.parser.from_url(source_url)
            if source_url else self.parser.from_content(source_content or {})
        )
        parsed = self.parser.parse(spec, tags=tags)
        preview_id = uuid4().hex
        self._preview_cache[preview_id] = parsed
        existing = await self._find_existing_cases(suite_id, parsed)
        existing_keys = {(op.method, op.path) for op in existing}
        new_count = sum(
            1 for op in parsed.operations
            if (op.method, op.path) not in existing_keys
        )
        ops_preview = [
            OperationPreview(
                operation_id=op.operation_id,
                method=op.method,
                path=op.path,
                name=op.name,
                status="new" if (op.method, op.path) not in existing_keys else "exists",
            )
            for op in parsed.operations
        ]
        return ImportPreviewResponse(
            spec_version=parsed.version,
            suite_id=suite_id,
            suite_name="",
            base_path=parsed.base_path,
            total=len(parsed.operations),
            new_count=new_count,
            existing_count=len(parsed.operations) - new_count,
            skipped_count=0,
            operations=ops_preview,
            errors=[],
        )

    async def import_from_preview(
        self,
        *,
        project_id: UUID,
        suite_id: UUID,
        preview_id: str,
        on_conflict: str = "skip",
        name_prefix: Optional[str] = None,
        current_user: User,
    ) -> ImportResponse:
        await self._load_project_suite(project_id, suite_id, current_user)
        parsed = self._preview_cache.pop(preview_id, None)
        if parsed is None:
            raise OpenApiImportConflictError(
                "preview expired or not found, re-issue preview"
            )
        existing = await self._find_existing_cases(suite_id, parsed)
        existing_map = {(op.method, op.path): op for op in existing}

        created: list[str] = []
        skipped: list[str] = []
        overwritten: list[str] = []
        errors: list[str] = []

        for op in parsed.operations:
            key = (op.method, op.path)
            existing_op = existing_map.get(key)
            case_name = f"{name_prefix or 'openapi'}: {op.name}"[:200]
            if existing_op is not None:
                if on_conflict == "skip":
                    skipped.append(op.name)
                    continue
                try:
                    await self.test_case_service.delete_test_case(
                        existing_op.id,
                        current_user=current_user,
                    )
                except Exception as exc:
                    errors.append(f"{op.name}: {exc}")
                    continue
                overwritten.append(op.name)
            try:
                create_req = TestCaseCreateRequest(
                    name=case_name,
                    method=op.method,
                    path=op.path,
                    headers=op.request_headers or None,
                    query_params=op.request_query or None,
                    body_type=op.request_body_type,
                    body=op.request_body,
                    assertions=[{
                        "type": "status_code",
                        "operator": "in",
                        "expected": [200, 201, 202, 204],
                    }],
                    timeout_seconds=30,
                )
                await self.test_case_service.create_test_case(
                    suite_id=suite_id,
                    request=create_req,
                    current_user=current_user,
                )
                created.append(op.name)
            except Exception as exc:
                errors.append(f"{op.name}: {exc}")

        return ImportResponse(
            created=created,
            skipped=skipped,
            overwritten=overwritten,
            errors=errors,
            total_attempted=len(parsed.operations),
            total_succeeded=len(created) + len(overwritten),
        )

    async def _load_project_suite(
        self, project_id: UUID, suite_id: UUID, current_user: User
    ) -> None:
        try:
            project = await self.project_service.get_project(
                project_id, current_user=current_user
            )
        except ProjectNotFoundException:
            raise ProjectNotFoundException()
        if not (
            current_user.is_superuser or project.owner_id == current_user.id
        ):
            raise ForbiddenException(
                "Only project owner or admin may import"
            )
        suite = await self.suite_service.get_suite(
            suite_id, current_user=current_user
        )
        if suite.project_id != project_id:
            raise ProjectNotFoundException()

    async def _find_existing_cases(
        self, suite_id: UUID, parsed: ParsedSpec
    ) -> list[ApiTestCase]:
        suite = await SuiteRepository(self.session).get_by_id(suite_id)
        if suite is None:
            return []
        keys = {(op.method, op.path) for op in parsed.operations}
        if not keys:
            return []
        rows = (await self.session.execute(
            select(ApiTestCase).where(ApiTestCase.project_id == suite.project_id)
        )).scalars().all()
        return [r for r in rows if (r.method, r.path) in keys]
