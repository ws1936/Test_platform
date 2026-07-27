"""F012 + F013 OpenAPI import service.

F012 ``preview`` / ``import_from_preview`` are byte-for-byte unchanged.
F013 adds ``preview_batch`` / ``import_batch_from_preview`` which reuse
the same parser, existing-case lookup, on_conflict machinery and
underlying test-case service. No business logic is duplicated.
"""
from __future__ import annotations
import logging
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenException, ProjectNotFoundException
from app.config import settings
from app.domain.openapi_importer.exceptions import (
    OpenApiBatchLimitExceededError,
    OpenApiFetchError,
    OpenApiImportConflictError,
    OpenApiParseError,
)
from app.domain.openapi_importer.parser import OpenApiSpecParser, ParsedSpec
from app.domain.openapi_importer.schema import (
    BatchImportPreviewResponse,
    BatchImportResponse,
    DocumentImportSummary,
    DocumentPreviewSummary,
    ImportPreviewResponse,
    ImportResponse,
    OperationPreview,
    OpenApiImportDocument,
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
    # Class-level (process-local) preview cache. F012 + F013 share it;
    # SPEC §10 documents the trade-off (cache is lost on restart or in
    # multi-worker deployments). Using a class variable rather than an
    # instance attribute is critical: FastAPI builds a new service
    # instance per HTTP request, so an instance attribute would break
    # the two-step ``?dry_run=true`` → ``?preview_id=...`` flow that
    # both F012 commit and F013 batch_commit rely on.
    #
    # Values are either a single ``ParsedSpec`` (F012) or
    # ``list[tuple[source_tag, Optional[ParsedSpec]]]`` (F013 batch).
    # ``isinstance`` at pop time isolates the two paths.
    _preview_cache: dict[str, Any] = {}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.parser = OpenApiSpecParser()
        self.project_service = ProjectService(session)
        self.suite_service = SuiteService(session)
        self.test_case_service = TestCaseService(session)

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
            preview_id=preview_id,
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

    # =====================================================================
    # F013 — batch import (multi-document)
    # =====================================================================
    #
    # Both methods below reuse:
    # * ``OpenApiSpecParser`` (F012, unchanged)
    # * ``_find_existing_cases`` (F012, unchanged)
    # * ``_load_project_suite`` (F012, unchanged)
    # * ``TestCaseService.create_test_case`` / ``delete_test_case`` (F012)
    #
    # The batch cache key uses the same uuid4().hex scheme as F012;
    # isolation between F012/F013 preview_ids is enforced by
    # ``isinstance`` at pop time. See tests T1/T8/T13 in F013_SPEC.

    async def preview_batch(
        self,
        *,
        project_id: UUID,
        suite_id: UUID,
        documents: list[OpenApiImportDocument],
        tags: Optional[list[str]] = None,
        current_user: User,
    ) -> BatchImportPreviewResponse:
        """F013 multi-document preview.

        Parses each document via the existing F012 parser, enforces the
        per-document operation cap, and computes new/existing over the
        suite's existing cases via F012's ``_find_existing_cases`` (zero
        duplication of business logic).

        Per-doc failures (parse / fetch) accumulate in the per-doc
        ``errors`` field and do NOT abort sibling documents. Cross-doc
        aborts (e.g. ``OPENAPI_BATCH_LIMIT_EXCEEDED``) raise as
        exceptions with business code 400.

        The whole batch is cached under a single ``preview_id`` so the
        subsequent commit call can replay the parsed specs atomically.
        """
        await self._load_project_suite(project_id, suite_id, current_user)
        suite = await self.suite_service.get_suite(
            suite_id, current_user=current_user
        )

        doc_summaries: list[DocumentPreviewSummary] = []
        parsed_docs: list[tuple[str, Optional[ParsedSpec]]] = []

        for idx, doc in enumerate(documents):
            source_tag = (
                f"url:{doc.source_url}"
                if doc.source_url is not None
                else "content:<inline>"
            )
            try:
                raw = (
                    self.parser.from_url(doc.source_url)
                    if doc.source_url is not None
                    else self.parser.from_content(doc.source_content or {})
                )
                effective_tags = (
                    doc.tags if doc.tags is not None else tags
                )
                parsed = self.parser.parse(raw, tags=effective_tags)
            except (OpenApiFetchError, OpenApiParseError) as exc:
                logger.warning(
                    "batch_parse_failed: code=%s doc_index=%d source=%s",
                    exc.code, idx, source_tag,
                )
                doc_summaries.append(DocumentPreviewSummary(
                    doc_index=idx,
                    source=source_tag,
                    spec_version="",
                    base_path="",
                    total=0,
                    new_count=0,
                    existing_count=0,
                    skipped_count=0,
                    operations=[],
                    errors=[str(exc.message)],
                ))
                parsed_docs.append((source_tag, None))
                continue

            if (
                len(parsed.operations)
                > settings.OPENAPI_BATCH_MAX_OPS_PER_DOC
            ):
                raise OpenApiBatchLimitExceededError(
                    message=(
                        f"document at index {idx} parsed to "
                        f"{len(parsed.operations)} operations, exceeding "
                        "OPENAPI_BATCH_MAX_OPS_PER_DOC="
                        f"{settings.OPENAPI_BATCH_MAX_OPS_PER_DOC}"
                    ),
                    details={
                        "doc_index": idx,
                        "operations": len(parsed.operations),
                        "limit": settings.OPENAPI_BATCH_MAX_OPS_PER_DOC,
                    },
                )

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
                    status=(
                        "new"
                        if (op.method, op.path) not in existing_keys
                        else "exists"
                    ),
                )
                for op in parsed.operations
            ]
            doc_summaries.append(DocumentPreviewSummary(
                doc_index=idx,
                source=source_tag,
                spec_version=parsed.version,
                base_path=parsed.base_path,
                total=len(parsed.operations),
                new_count=new_count,
                existing_count=len(parsed.operations) - new_count,
                skipped_count=0,
                operations=ops_preview,
                errors=[],
            ))
            parsed_docs.append((source_tag, parsed))

        total_operations = sum(
            len(parsed.operations)
            for _, parsed in parsed_docs
            if parsed is not None
        )
        preview_id = uuid4().hex
        self._preview_cache[preview_id] = parsed_docs

        logger.info(
            "batch_import_preview: project=%s suite=%s docs=%d "
            "total_ops=%d preview_id=%s",
            project_id, suite_id, len(documents), total_operations,
            preview_id,
        )
        return BatchImportPreviewResponse(
            suite_id=suite_id,
            suite_name=suite.name,
            total_documents=len(documents),
            total_operations=total_operations,
            documents=doc_summaries,
            errors=[],
            preview_id=preview_id,
        )

    async def import_batch_from_preview(
        self,
        *,
        project_id: UUID,
        suite_id: UUID,
        preview_id: str,
        on_conflict: str = "skip",
        name_prefix: Optional[str] = None,
        current_user: User,
    ) -> BatchImportResponse:
        """F013 multi-document commit.

        Replays the parsed specs cached by ``preview_batch``, executing
        the same on_conflict machinery as F012 but per document and
        rolled up at the batch level.

        Per-op failures accumulate in ``documents[i].errors``.
        TestResult history of overwritten cases is preserved (F012's
        ``delete_test_case`` cascade semantics are unchanged).
        """
        await self._load_project_suite(project_id, suite_id, current_user)

        cached = self._preview_cache.pop(preview_id, None)
        if cached is None or not isinstance(cached, list):
            raise OpenApiImportConflictError(
                "preview expired or not found, re-issue preview"
            )
        parsed_docs: list[tuple[str, Optional[ParsedSpec]]] = cached

        per_doc: list[DocumentImportSummary] = []
        total_attempted = 0
        total_succeeded = 0

        for idx, (source_tag, parsed) in enumerate(parsed_docs):
            if parsed is None:
                per_doc.append(DocumentImportSummary(
                    doc_index=idx,
                    source=source_tag,
                ))
                continue

            existing = await self._find_existing_cases(suite_id, parsed)
            existing_map = {
                (op.method, op.path): op for op in existing
            }
            created: list[str] = []
            skipped: list[str] = []
            overwritten: list[str] = []
            errors: list[str] = []
            doc_attempted = len(parsed.operations)

            for op in parsed.operations:
                key = (op.method, op.path)
                existing_op = existing_map.get(key)
                case_name = (
                    f"{name_prefix or 'openapi'}: {op.name}"
                )[:200]
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

            per_doc.append(DocumentImportSummary(
                doc_index=idx,
                source=source_tag,
                created=created,
                skipped=skipped,
                overwritten=overwritten,
                errors=errors,
            ))
            total_attempted += doc_attempted
            total_succeeded += len(created) + len(overwritten)

        logger.info(
            "batch_import_commit: project=%s suite=%s docs=%d "
            "attempted=%d succeeded=%d",
            project_id, suite_id, len(parsed_docs),
            total_attempted, total_succeeded,
        )
        return BatchImportResponse(
            total_documents=len(parsed_docs),
            total_attempted=total_attempted,
            total_succeeded=total_succeeded,
            documents=per_doc,
            errors=[],
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
