"""F012 OpenAPI import Pydantic schemas."""
from __future__ import annotations
from typing import Any, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


ImportConflictStrategy = Literal["skip", "overwrite"]


class OpenApiImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_url: Optional[str] = Field(default=None, description="OpenAPI spec URL")
    source_content: Optional[dict[str, Any]] = Field(default=None, description="Parsed spec")
    tags: Optional[list[str]] = Field(default=None, description="Filter operations by tag")
    on_conflict: ImportConflictStrategy = Field(default="skip")
    dry_run: bool = Field(default=True)
    name_prefix: Optional[str] = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def _check_source(self) -> "OpenApiImportRequest":
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
