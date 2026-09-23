"""F012 + F013 + F023 OpenAPI import service.

F012 ``preview`` / ``import_from_preview`` are byte-for-byte unchanged
when ``?design=simple`` (default). F013 adds ``preview_batch`` /
``import_batch_from_preview`` which reuse the same parser, existing-case
lookup, on_conflict machinery and underlying test-case service. No
business logic is duplicated.

F023 (ADR-009) adds an optional ``design`` parameter on all four
public methods:

* ``design="simple"`` (default) → F012/F013 path, byte-for-byte unchanged.
* ``design="schema"`` → schema-driven generation:
    - ``SchemaAnalyzer.analyze`` builds ``EndpointSchema`` per operation
    - ``TestDesignEngine.design`` produces ``list[TestIntent]``
    - ``TestGenerator`` turns each intent into ``TestCaseCreateRequest``
    - per-operation intent cap is enforced via
      ``settings.generator_max_intents_per_operation`` (F022 §7).

The cache only stores the parsed spec; intent generation is repeatable
from the spec + ``components.schemas`` etc. — committing re-runs the
analysis. This keeps the cache structure unchanged and preserves F012's
"byte-for-byte" guarantee for the simple path.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenException, ProjectNotFoundException
from app.config import settings
from app.domain.openapi_importer.exceptions import (
    OpenApiBatchLimitExceededError, OpenApiFetchError,
    OpenApiImportConflictError, OpenApiIntentLimitExceededError,
    OpenApiParseError)
from app.domain.openapi_importer.parser import OpenApiSpecParser, ParsedSpec
from app.domain.openapi_importer.schema import (BatchImportPreviewResponse,
                                                BatchImportResponse,
                                                DocumentImportSummary,
                                                DocumentPreviewSummary,
                                                ImportPreviewResponse,
                                                ImportResponse,
                                                OpenApiImportDocument,
                                                OperationPreview)
from app.domain.openapi_importer.schema_analyzer import SchemaAnalyzer
from app.domain.openapi_importer.schema_model import EndpointSchema
from app.domain.project.service import ProjectService
from app.domain.suite.repository import SuiteRepository
from app.domain.suite.service import SuiteService
from app.domain.test_case.model import ApiTestCase
from app.domain.test_case.schema import TestCaseCreateRequest
from app.domain.test_case.service import TestCaseService
from app.domain.test_design.engine import TestDesignEngine
from app.domain.test_design.schema import TestIntent
from app.domain.test_generator import TestGenerator
from app.domain.user.model import User

# F023 design-mode literal (ADR-009 decision 1).
DesignMode = Literal["simple", "schema"]


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
        # F023: SchemaAnalyzer / TestDesignEngine are stateless, but we hold
        # instances to avoid re-instantiating per call. They take their
        # configuration from ``settings`` at construction time.
        self._schema_analyzer = SchemaAnalyzer()
        self._design_engine = TestDesignEngine(settings)
        self._generator = TestGenerator()

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
        design: DesignMode = "simple",
    ) -> ImportPreviewResponse:
        await self._load_project_suite(project_id, suite_id, current_user)
        spec = (
            self.parser.from_url(source_url)
            if source_url
            else self.parser.from_content(source_content or {})
        )
        parsed = self.parser.parse(spec, tags=tags)
        preview_id = uuid4().hex
        self._preview_cache[preview_id] = parsed
        existing = await self._find_existing_cases(suite_id, parsed)
        existing_keys = {(op.method, op.path) for op in existing}
        new_count = sum(
            1 for op in parsed.operations if (op.method, op.path) not in existing_keys
        )

        # F023 design="schema": enrich each OperationPreview with the
        # strategy of the corresponding TestIntent(s) and compute the
        # total_intents counter. The per-operation intent cap is enforced
        # here so the user gets the error BEFORE committing (preview is
        # cheap to retry).
        ops_preview: list[OperationPreview] = []
        total_intents: Optional[int] = None
        if design == "schema":
            ops_preview, total_intents = self._build_schema_preview_ops(
                parsed=parsed,
                existing_keys=existing_keys,
            )
        else:
            ops_preview = [
                OperationPreview(
                    operation_id=op.operation_id,
                    method=op.method,
                    path=op.path,
                    name=op.name,
                    status=(
                        "new" if (op.method, op.path) not in existing_keys else "exists"
                    ),
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
            total_intents=total_intents,
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
        design: DesignMode = "simple",
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
            base_name = f"{name_prefix or 'openapi'}: {op.name}"[:200]
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
                if design == "schema":
                    # F023 path: re-analyze + re-design + TestGenerator.
                    # The analysis is pure so re-running it on commit is
                    # safe; we deliberately do NOT cache intents so the
                    # preview cache structure remains F012 byte-stable.
                    create_reqs = self._build_schema_create_requests(
                        op=op,
                        name_prefix=name_prefix,
                        parsed=parsed,
                    )
                else:
                    # F012 byte-for-byte path.
                    create_reqs = [
                        TestCaseCreateRequest(
                            name=base_name,
                            method=op.method,
                            path=op.path,
                            headers=op.request_headers or None,
                            query_params=op.request_query or None,
                            body_type=op.request_body_type,
                            body=op.request_body,
                            assertions=[
                                {
                                    "type": "status_code",
                                    "operator": "in",
                                    "expected": [200, 201, 202, 204],
                                }
                            ],
                            timeout_seconds=30,
                        )
                    ]
                for create_req in create_reqs:
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
        design: DesignMode = "simple",
    ) -> BatchImportPreviewResponse:
        """F013 multi-document preview + F023 design="schema" expansion.

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

        F023 (ADR-009 decision 4): when ``design="schema"`` and any
        operation exceeds ``generator_max_intents_per_operation``, the
        *whole batch* is aborted (not just that document) — intent
        overflow is platform protection, not data error.
        """
        await self._load_project_suite(project_id, suite_id, current_user)
        suite = await self.suite_service.get_suite(suite_id, current_user=current_user)

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
                effective_tags = doc.tags if doc.tags is not None else tags
                parsed = self.parser.parse(raw, tags=effective_tags)
            except (OpenApiFetchError, OpenApiParseError) as exc:
                logger.warning(
                    "batch_parse_failed: code=%s doc_index=%d source=%s",
                    exc.code,
                    idx,
                    source_tag,
                )
                doc_summaries.append(
                    DocumentPreviewSummary(
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
                        total_intents=0,
                    )
                )
                parsed_docs.append((source_tag, None))
                continue

            if len(parsed.operations) > settings.OPENAPI_BATCH_MAX_OPS_PER_DOC:
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
                1
                for op in parsed.operations
                if (op.method, op.path) not in existing_keys
            )
            # F023 design="schema" → expand operations[] per intent.
            if design == "schema":
                ops_preview, total_intents = self._build_schema_preview_ops(
                    parsed=parsed,
                    existing_keys=existing_keys,
                )
            else:
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
                total_intents = None
            doc_summaries.append(
                DocumentPreviewSummary(
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
                    total_intents=total_intents,
                )
            )
            parsed_docs.append((source_tag, parsed))

        total_operations = sum(
            len(parsed.operations) for _, parsed in parsed_docs if parsed is not None
        )
        total_intents_all: Optional[int] = (
            sum(s.total_intents or 0 for s in doc_summaries) or None
        )
        preview_id = uuid4().hex
        self._preview_cache[preview_id] = parsed_docs

        logger.info(
            "batch_import_preview: project=%s suite=%s docs=%d "
            "total_ops=%d total_intents=%s preview_id=%s",
            project_id,
            suite_id,
            len(documents),
            total_operations,
            total_intents_all,
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
            total_intents=total_intents_all,
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
        design: DesignMode = "simple",
    ) -> BatchImportResponse:
        """F013 multi-document commit + F023 design="schema" expansion.

        Replays the parsed specs cached by ``preview_batch``, executing
        the same on_conflict machinery as F012 but per document and
        rolled up at the batch level.

        Per-op failures accumulate in ``documents[i].errors``.
        TestResult history of overwritten cases is preserved (F012's
        ``delete_test_case`` cascade semantics are unchanged).

        F023 (ADR-009): when ``design="schema"`` is in effect, each
        operation produces N ``TestCaseCreateRequest`` via
        ``TestGenerator``. The (method, path) uniqueness check still
        gates all N intents together (skip = skip all, overwrite =
        delete + recreate all).
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
                per_doc.append(
                    DocumentImportSummary(
                        doc_index=idx,
                        source=source_tag,
                    )
                )
                continue

            existing = await self._find_existing_cases(suite_id, parsed)
            existing_map = {(op.method, op.path): op for op in existing}
            created: list[str] = []
            skipped: list[str] = []
            overwritten: list[str] = []
            errors: list[str] = []
            doc_attempted = len(parsed.operations)

            for op in parsed.operations:
                key = (op.method, op.path)
                existing_op = existing_map.get(key)
                base_name = (f"{name_prefix or 'openapi'}: {op.name}")[:200]
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
                    if design == "schema":
                        create_reqs = self._build_schema_create_requests(
                            op=op,
                            name_prefix=name_prefix,
                            parsed=parsed,
                        )
                    else:
                        create_reqs = [
                            TestCaseCreateRequest(
                                name=base_name,
                                method=op.method,
                                path=op.path,
                                headers=op.request_headers or None,
                                query_params=op.request_query or None,
                                body_type=op.request_body_type,
                                body=op.request_body,
                                assertions=[
                                    {
                                        "type": "status_code",
                                        "operator": "in",
                                        "expected": [200, 201, 202, 204],
                                    }
                                ],
                                timeout_seconds=30,
                            )
                        ]
                    for create_req in create_reqs:
                        await self.test_case_service.create_test_case(
                            suite_id=suite_id,
                            request=create_req,
                            current_user=current_user,
                        )
                    created.append(op.name)
                except Exception as exc:
                    errors.append(f"{op.name}: {exc}")

            per_doc.append(
                DocumentImportSummary(
                    doc_index=idx,
                    source=source_tag,
                    created=created,
                    skipped=skipped,
                    overwritten=overwritten,
                    errors=errors,
                )
            )
            total_attempted += doc_attempted
            total_succeeded += len(created) + len(overwritten)

        logger.info(
            "batch_import_commit: project=%s suite=%s docs=%d "
            "attempted=%d succeeded=%d",
            project_id,
            suite_id,
            len(parsed_docs),
            total_attempted,
            total_succeeded,
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
        if not (current_user.is_superuser or project.owner_id == current_user.id):
            raise ForbiddenException("Only project owner or admin may import")
        suite = await self.suite_service.get_suite(suite_id, current_user=current_user)
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
        rows = (
            (
                await self.session.execute(
                    select(ApiTestCase).where(
                        ApiTestCase.project_id == suite.project_id
                    )
                )
            )
            .scalars()
            .all()
        )
        return [r for r in rows if (r.method, r.path) in keys]

    # =====================================================================
    # F023 — design="schema" helpers (ADR-009)
    # =====================================================================
    #
    # These helpers take the F012 ``ParsedSpec`` (already cached for the
    # ``preview_id`` → ``?dry_run=false`` commit flow) and re-run the
    # ``SchemaAnalyzer`` + ``TestDesignEngine`` + ``TestGenerator`` chain.
    # Pure functions over the cached spec, so no DB writes happen during
    # the analysis pass — we only enforce the intent cap and emit the
    # preview items.

    def _build_schema_preview_ops(
        self,
        *,
        parsed: ParsedSpec,
        existing_keys: set[tuple[str, str]],
    ) -> tuple[list[OperationPreview], int]:
        """Build per-intent ``OperationPreview`` items + total intent count.

        Enforces ``settings.generator_max_intents_per_operation`` per
        operation: if any operation exceeds the cap, raise
        ``OpenApiIntentLimitExceededError`` (HTTP 400, code
        ``GENERATOR_INTENT_LIMIT_EXCEEDED``) — ADR-009 decision 4:
        abort the whole batch/preview, not per-operation isolation.
        """
        components_schemas, security_schemes, global_security = (
            self._extract_spec_components(parsed)
        )
        ops_preview: list[OperationPreview] = []
        total = 0
        for op in parsed.operations:
            endpoint = self._schema_analyzer.analyze(
                op,
                components_schemas=components_schemas,
                security_schemes=security_schemes,
                global_security=global_security,
            )
            intents = self._design_engine.design(endpoint)
            if len(intents) > settings.generator_max_intents_per_operation:
                logger.warning(
                    "generator_intent_cap_hit: operation=%s %s produced=%d cap=%d",
                    op.method,
                    op.path,
                    len(intents),
                    settings.generator_max_intents_per_operation,
                )
                raise OpenApiIntentLimitExceededError(
                    message=(
                        f"operation {op.method} {op.path} produced "
                        f"{len(intents)} intents, exceeding "
                        "generator_max_intents_per_operation="
                        f"{settings.generator_max_intents_per_operation}"
                    ),
                    details={
                        "method": op.method,
                        "path": op.path,
                        "produced": len(intents),
                        "cap": settings.generator_max_intents_per_operation,
                    },
                )
            status_label = (
                "new" if (op.method, op.path) not in existing_keys else "exists"
            )
            for intent in intents:
                ops_preview.append(
                    OperationPreview(
                        operation_id=op.operation_id,
                        method=op.method,
                        path=op.path,
                        name=intent.name,
                        status=status_label,
                        strategy=intent.strategy,
                    )
                )
            total += len(intents)
        return ops_preview, total

    def _build_schema_create_requests(
        self,
        *,
        op: Any,  # Operation; using Any to avoid local import
        name_prefix: Optional[str],
        parsed: ParsedSpec,
    ) -> list[TestCaseCreateRequest]:
        """Build ``TestCaseCreateRequest`` list for one operation.

        Re-runs SchemaAnalyzer + TestDesignEngine + TestGenerator
        (pure; safe to repeat on commit). Cap enforcement already
        happened in ``preview_batch`` / ``preview``; this helper assumes
        we are below the cap.
        """
        components_schemas, security_schemes, global_security = (
            self._extract_spec_components(parsed)
        )
        endpoint = self._schema_analyzer.analyze(
            op,
            components_schemas=components_schemas,
            security_schemes=security_schemes,
            global_security=global_security,
        )
        intents = self._design_engine.design(endpoint)
        # When a custom ``name_prefix`` is supplied, prepend it to each
        # intent's name (mirror F012's "openapi: <name>" convention).
        # We use ``model_copy`` instead of mutating ``intent`` so the
        # upstream TestIntent remains untouched.
        if name_prefix is not None:
            intents = [
                intent.model_copy(
                    update={"name": f"{name_prefix}: {intent.name}"[:200]}
                )
                for intent in intents
            ]
        return self._generator.intents_to_requests(
            intents=intents,
            operation=op,
            endpoint=endpoint,
        )

    @staticmethod
    def _extract_spec_components(
        parsed: ParsedSpec,
    ) -> tuple[
        Optional[dict[str, Any]],
        Optional[dict[str, Any]],
        Optional[list[dict[str, list[str]]]],
    ]:
        """Pull ``components.schemas`` / ``components.securitySchemes`` /
        global ``security`` out of the cached ``ParsedSpec.raw``."""
        components = parsed.raw.get("components") or {}
        schemas = components.get("schemas")
        schemes = components.get("securitySchemes")
        global_security = parsed.raw.get("security")
        return schemas, schemes, global_security
