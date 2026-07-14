"""F012 OpenAPI import router."""
from __future__ import annotations
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import get_current_user, get_openapi_import_service
from app.domain.openapi_importer.schema import (
    OpenApiImportRequest,
    ImportPreviewResponse,
    ImportResponse,
)
from app.domain.openapi_importer.service import OpenApiImportService
from app.domain.user.model import User


import_router = APIRouter(prefix="/projects", tags=["OpenAPI"])


@import_router.post(
    "/{project_id}/suites/{suite_id}/import/openapi",
    response_model=ImportPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview or import an OpenAPI spec into a suite",
)
async def preview_or_import_openapi(
    project_id: UUID,
    suite_id: UUID,
    request: OpenApiImportRequest,
    on_conflict: str = Query(default="skip"),
    dry_run: bool = Query(default=True),
    preview_id: Optional[str] = Query(default=None),
    name_prefix: Optional[str] = Query(default=None, max_length=80),
    service: OpenApiImportService = Depends(get_openapi_import_service),
    current_user: User = Depends(get_current_user),
):
    """MVP: one endpoint with ``?dry_run=true|false``.

    dry_run=true (default) → returns ``ImportPreviewResponse``,
    caches the parsed spec for the second call.

    dry_run=false (and ``preview_id`` provided) → creates the
    cases from the cached preview and returns ``ImportResponse``.
    """
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
