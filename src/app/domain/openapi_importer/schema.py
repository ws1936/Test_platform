"""F012 + F013 OpenAPI import Pydantic schemas.

F013 extends the F012 surface with ``OpenApiImportDocument`` and the
``BatchImportPreviewResponse`` / ``BatchImportResponse`` shapes used
when ``?batch=true``. The F012 single-document contract
(``OpenApiImportRequest`` / ``ImportPreviewResponse`` /
``ImportResponse`` / ``OperationPreview``) is kept byte-for-byte.
"""
from __future__ import annotations
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


ImportConflictStrategy = Literal["skip", "overwrite"]


class OpenApiImportDocument(BaseModel):
    """F013: a single OpenAPI document reference (element of ``documents[]``).

    Mirrors the XOR/URL-scheme contract that F012 enforces on the top-level
    request, but scoped to one element so per-document errors are local.
    """

    model_config = ConfigDict(extra="forbid")
    source_url: Optional[str] = Field(default=None)
    source_content: Optional[dict[str, Any]] = Field(default=None)
    tags: Optional[list[str]] = Field(default=None)
    name_prefix: Optional[str] = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def _check_source(self) -> "OpenApiImportDocument":
        if (self.source_url is None) == (self.source_content is None):
            raise ValueError("exactly one of source_url/source_content required")
        if self.source_url is not None:
            url = self.source_url.lower()
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(
                    "source_url must start with http:// or https://"
                )
        return self


class OpenApiImportRequest(BaseModel):
    """F012 single-doc / F013 batch OpenAPI import request.

    Behaviour:
        * If ``documents`` is None → F012 single-doc contract (unchanged).
        * If ``documents`` is set → F013 batch contract.
          ``documents`` is mutually exclusive with all single-doc fields
          (``source_url`` / ``source_content`` / ``tags`` / ``name_prefix``).
          ``documents`` must contain at least one element; the upper bound
          is enforced by ``settings.OPENAPI_BATCH_MAX_DOCS`` via Pydantic.
    """

    model_config = ConfigDict(extra="forbid")
    source_url: Optional[str] = Field(default=None, description="OpenAPI spec URL")
    source_content: Optional[dict[str, Any]] = Field(
        default=None, description="Parsed spec"
    )
    tags: Optional[list[str]] = Field(
        default=None, description="Filter operations by tag"
    )
    on_conflict: ImportConflictStrategy = Field(default="skip")
    dry_run: bool = Field(default=True)
    name_prefix: Optional[str] = Field(default=None, max_length=80)
    documents: Optional[list[OpenApiImportDocument]] = Field(
        default=None,
        description=(
            "F013 batch: 1..N OpenAPI documents (N = "
            "OPENAPI_BATCH_MAX_DOCS). Mutually exclusive with the "
            "single-doc fields above."
        ),
    )

    @model_validator(mode="after")
    def _check_source(self) -> "OpenApiImportRequest":
        # F013 batch path: skip the F012 XOR but enforce exclusivity.
        if self.documents is not None:
            if (
                self.source_url is not None
                or self.source_content is not None
                or self.tags is not None
                or self.name_prefix is not None
            ):
                raise ValueError(
                    "documents[] is mutually exclusive with "
                    "source_url/source_content/tags/name_prefix"
                )
            if not self.documents:
                raise ValueError("documents[] must contain at least one document")
            # The hard cap on documents length lives at the route entry /
            # is left to the runtime layer so we always surface a
            # business code, not a generic 422. Per-doc models already
            # validated source_url/source_content XOR and URL scheme.
            from app.config import settings  # local import avoids module cycle
            if len(self.documents) > settings.OPENAPI_BATCH_MAX_DOCS:
                raise ValueError(
                    f"documents[] length {len(self.documents)} exceeds "
                    f"OPENAPI_BATCH_MAX_DOCS={settings.OPENAPI_BATCH_MAX_DOCS}"
                )
            return self
        # F012 single-doc path: byte-for-byte preserved.
        if (self.source_url is None) == (self.source_content is None):
            raise ValueError("exactly one of source_url/source_content required")
        if self.source_url is not None:
            url = self.source_url.lower()
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError("source_url must start with http:// or https://")
        return self


class OperationPreview(BaseModel):
    operation_id: Optional[str]
    method: str
    path: str
    name: str
    status: str


class ImportPreviewResponse(BaseModel):
    preview_id: str = Field(
        description="Token required by the subsequent dry_run=false commit"
    )
    spec_version: str
    suite_id: UUID
    suite_name: str
    base_path: str
    total: int
    new_count: int
    existing_count: int
    skipped_count: int
    operations: list[OperationPreview]
    errors: list[str]


class ImportResponse(BaseModel):
    created: list[str]
    skipped: list[str]
    overwritten: list[str]
    errors: list[str]
    total_attempted: int
    total_succeeded: int


# ---------------------------------------------------------------------------
# F013 — batch import schemas
# ---------------------------------------------------------------------------


class DocumentPreviewSummary(BaseModel):
    """Per-document preview section in a batch preview response."""

    doc_index: int = Field(
        description="Index of this document in the request's documents[]"
    )
    source: str = Field(
        description=(
            "Lightweight provenance tag: 'url:<value>' for url-sourced "
            "documents or 'content:<sha256-prefix>' for inline docs"
        )
    )
    spec_version: str
    base_path: str
    total: int
    new_count: int
    existing_count: int
    skipped_count: int
    operations: list[OperationPreview]
    errors: list[str] = Field(
        default_factory=list,
        description="Per-document parse/validation errors; does not abort siblings",
    )


class BatchImportPreviewResponse(BaseModel):
    suite_id: UUID
    suite_name: str
    total_documents: int
    total_operations: int
    documents: list[DocumentPreviewSummary]
    errors: list[str] = Field(
        default_factory=list,
        description="Cross-document errors that prevented any parse (e.g. M limit)",
    )
    # F013 fix: the F012 ``preview`` does NOT expose ``preview_id``
    # in its response body, which makes the F012 commit path
    # end-to-end untestable (latent F012 bug, intentionally NOT fixed
    # here). F013 needs the preview_id to drive ``?batch=true&...``
    # commit, so we surface it explicitly. See F013_SPEC.md §4.3.1.
    preview_id: Optional[str] = Field(
        default=None,
        description=(
            "Required for the commit call (``?dry_run=false&preview_id=...``)."
            " Currently always populated by preview_batch."
        ),
    )


class DocumentImportSummary(BaseModel):
    """Per-document commit section in a batch commit response."""

    doc_index: int
    source: str
    created: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    overwritten: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BatchImportResponse(BaseModel):
    total_documents: int
    total_attempted: int
    total_succeeded: int
    documents: list[DocumentImportSummary]
    errors: list[str] = Field(default_factory=list)
