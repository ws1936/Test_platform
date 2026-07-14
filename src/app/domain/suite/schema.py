"""Pydantic request and response schemas for F006 suites."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)


class SuiteBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None


class SuiteCreateRequest(SuiteBase):
    """Create a project-scoped suite."""


class SuiteUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None


class SuiteCasesBulkCreate(BaseModel):
    """Bulk append case IDs; duplicate IDs are intentionally accepted."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    test_case_ids: list[UUID] = Field(
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("test_case_ids", "case_ids"),
    )


class SuiteCaseOrderItem(BaseModel):
    """One explicit case/order pair accepted by the reorder endpoint."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    test_case_id: UUID = Field(validation_alias=AliasChoices("test_case_id", "case_id"))
    order: int = Field(
        ge=0,
        validation_alias=AliasChoices("order", "sort_order"),
    )


class SuiteCasesReorderRequest(BaseModel):
    """Reorder cases either by an ID list or explicit order records.

    Supported JSON shapes are ``{"test_case_ids": [...]}``,
    ``{"case_ids": [...]}``, and ``{"cases": [{"case_id": ..., "order": 0}]}``.
    The aliases make the endpoint tolerant of both names used in early API
    drafts while keeping one normalized service contract.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    test_case_ids: Optional[list[UUID]] = Field(
        default=None,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("test_case_ids", "case_ids"),
    )
    cases: Optional[list[SuiteCaseOrderItem]] = Field(
        default=None,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("cases", "orders", "case_orders"),
    )

    @model_validator(mode="after")
    def validate_single_shape(self) -> "SuiteCasesReorderRequest":
        if (self.test_case_ids is None) == (self.cases is None):
            raise ValueError("provide exactly one of case_ids/test_case_ids or cases")
        ids = self.ordered_test_case_ids
        if len(ids) != len(set(ids)):
            raise ValueError("case IDs in a reorder request must be unique")
        return self

    @property
    def ordered_test_case_ids(self) -> list[UUID]:
        if self.test_case_ids is not None:
            return list(self.test_case_ids)
        assert self.cases is not None
        return [item.test_case_id for item in sorted(self.cases, key=lambda x: x.order)]


class SuiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: Optional[str] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class SuiteCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    suite_id: UUID
    test_case_id: UUID
    order: int
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def case_id(self) -> UUID:
        """Compatibility alias for clients using ``case_id``."""
        return self.test_case_id

    @computed_field
    @property
    def sort_order(self) -> int:
        """Compatibility alias for the former response field."""
        return self.order


class SuiteDetailResponse(SuiteResponse):
    """Suite metadata plus its ordered case associations."""

    cases: list[SuiteCaseResponse]


class SuiteListResponse(BaseModel):
    items: list[SuiteResponse]
    total: int


class SuiteCasesBulkResponse(BaseModel):
    added: list[SuiteCaseResponse]
    already_present: list[UUID]
