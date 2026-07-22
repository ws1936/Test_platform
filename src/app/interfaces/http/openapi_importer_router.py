"""F012 OpenAPI import router."""
from __future__ import annotations
from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import get_current_user, get_openapi_import_service
from app.domain.openapi_importer.schema import (
    BatchImportPreviewResponse,
    BatchImportResponse,
    ImportPreviewResponse,
    ImportResponse,
    OpenApiImportRequest,
)
from app.domain.openapi_importer.service import OpenApiImportService
from app.domain.user.model import User


import_router = APIRouter(prefix="/projects", tags=["OpenAPI"])


@import_router.post(
    "/{project_id}/suites/{suite_id}/import/openapi",
    response_model=Union[
        ImportPreviewResponse,
        ImportResponse,
        BatchImportPreviewResponse,
        BatchImportResponse,
    ],
    status_code=status.HTTP_200_OK,
    summary=(
        "F012 single-doc / F013 batch OpenAPI import "
        "(?batch=true enables multi-document batch mode)"
    ),
)
async def preview_or_import_openapi(
    project_id: UUID,
    suite_id: UUID,
    request: OpenApiImportRequest,
    batch: bool = Query(
        default=False,
        description=(
            "F013 batch flag. false/omitted → F012 single-doc mode; "
            "true → F013 batch mode (request must carry documents[])."
        ),
    ),
    on_conflict: str = Query(default="skip"),
    dry_run: bool = Query(default=True),
    preview_id: Optional[str] = Query(default=None),
    name_prefix: Optional[str] = Query(default=None, max_length=80),
    service: OpenApiImportService = Depends(get_openapi_import_service),
    current_user: User = Depends(get_current_user),
):
    """F012 + F013 unified entry point.

    Without ``?batch=true`` (F012 single-doc, unchanged):
        - ``source_url`` XOR ``source_content`` is required.
        - ``?dry_run=true`` (default) → returns ``ImportPreviewResponse``
          and caches the parsed spec.
        - ``?dry_run=false&preview_id=...`` → creates the cases from
          the cached preview and returns ``ImportResponse``.

    With ``?batch=true`` (F013 multi-document):
        - request must carry ``documents[]`` (mutually exclusive with
          the F012 single-doc fields; enforced by the request schema).
        - ``?dry_run=true`` (default) → returns
          ``BatchImportPreviewResponse`` and caches all parsed specs
          under one ``preview_id``.
        - ``?dry_run=false&preview_id=...`` → creates cases per
          document and returns ``BatchImportResponse``.
        - Per-document errors do not abort sibling documents.

    See ``docs/01-product/F013_SPEC.md`` for the full contract.
    """
    if batch:
        if dry_run or preview_id is None:
            return await service.preview_batch(
                project_id=project_id,
                suite_id=suite_id,
                documents=request.documents or [],
                tags=request.tags,
                current_user=current_user,
            )
        return await service.import_batch_from_preview(
            project_id=project_id,
            suite_id=suite_id,
            preview_id=preview_id,
            on_conflict=on_conflict,
            name_prefix=name_prefix,
            current_user=current_user,
        )
    # F012 single-doc path: byte-for-byte preserved.
    if dry_run or preview_id is None:
        return await service.preview(
            project_id=project_id,
            suite_id=suite_id,
            source_url=request.source_url,
            source_content=request.source_content,
            tags=request.tags,
            on_conflict=on_conflict,
            current_user=current_user,
        )
    return await service.import_from_preview(
        project_id=project_id,
        suite_id=suite_id,
        preview_id=preview_id,
        on_conflict=on_conflict,
        name_prefix=name_prefix,
        current_user=current_user,
    )
