"""Project service for F004 — API testing project management.

Business rules implemented here:

* On create, ``owner_id`` is always set from ``current_user.id``;
  the client cannot forge ownership through the request schema.
* List is **scoped to the authenticated user** — every login sees only
  their own projects. Admins (superusers) also see only their own
  projects in the MVP (cross-owner views are out of scope).
* Get / update / delete: only the project owner or a superuser may
  access the record. Everyone else gets ``403 Forbidden``.
* ProjectNotFoundException (30001) is raised when the record does not
  exist; we deliberately do NOT collapse 404 into 403 to avoid
  information leaks about which project IDs are valid.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenException, ProjectNotFoundException
from app.domain.project.model import ApiProject
from app.domain.project.repository import ProjectRepository
from app.domain.project.schema import (
    ProjectCreateRequest,
    ProjectListQuery,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.domain.user.model import User


logger = logging.getLogger(__name__)


def _audit(
    event: str,
    *,
    project_id: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> None:
    """Emit a structured audit log line without leaking secrets."""
    fields = {"event": event}
    if project_id is not None:
        fields["project_id"] = project_id
    if actor_id is not None:
        fields["actor_id"] = actor_id
    logger.info("project.audit %s", fields)


class ProjectService:
    """Project business logic for F004."""

    def __init__(self, session: AsyncSession):
        self.repository = ProjectRepository(session)
        self.session = session

    # === Create ===

    async def create_project(
        self,
        request: ProjectCreateRequest,
        *,
        current_user: User,
    ) -> ProjectResponse:
        """Create a new project owned by ``current_user``."""
        project = ApiProject(
            name=request.name,
            description=request.description,
            owner_id=current_user.id,
        )
        project = await self.repository.create(project)
        await self.session.commit()
        _audit("create", project_id=str(project.id), actor_id=str(current_user.id))
        return ProjectResponse.model_validate(project)

    # === Read ===

    async def get_project(
        self,
        project_id: UUID,
        *,
        current_user: User,
    ) -> ApiProject:
        """Fetch a project by ID.

        Authorization: project owner or superuser. Non-owners get
        ``403 Forbidden``.

        Raises:
            ProjectNotFoundException: when the project does not exist.
            ForbiddenException: when the caller is neither owner nor admin.
        """
        project = await self.repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundException()
        self._assert_can_view(project, current_user)
        return project

    async def list_projects(
        self,
        query: ProjectListQuery,
        *,
        current_user: User,
    ) -> ProjectListResponse:
        """List projects owned by ``current_user`` (paginated, searchable).

        The list is always scoped to the authenticated user's own
        projects; an explicit ``owner_id`` filter is not exposed at the
        API surface.
        """
        items, total = await self.repository.list_paginated(
            page=query.page,
            size=query.size,
            search=query.search,
            owner_id=current_user.id,
        )
        return ProjectListResponse(
            items=[ProjectResponse.model_validate(p) for p in items],
            total=total,
            page=query.page,
            size=query.size,
        )

    # === Update ===

    async def update_project(
        self,
        project_id: UUID,
        request: ProjectUpdateRequest,
        *,
        current_user: User,
    ) -> ProjectResponse:
        """Update a project (name / description).

        Authorization: project owner or superuser.
        """
        project = await self.get_project(project_id, current_user=current_user)
        self._assert_can_modify(project, current_user)

        if request.name is not None:
            project.name = request.name
        if request.description is not None:
            project.description = request.description

        project = await self.repository.update(project)
        await self.session.commit()
        _audit("update", project_id=str(project.id), actor_id=str(current_user.id))
        return ProjectResponse.model_validate(project)

    # === Delete ===

    async def delete_project(
        self,
        project_id: UUID,
        *,
        current_user: User,
    ) -> None:
        """Hard-delete a project.

        Authorization: project owner or superuser.

        Raises:
            ProjectNotFoundException: when the project does not exist.
            ForbiddenException: when the caller is neither owner nor admin.
        """
        project = await self.get_project(project_id, current_user=current_user)
        self._assert_can_modify(project, current_user)

        await self.repository.delete(project)
        await self.session.commit()
        _audit("delete", project_id=str(project_id), actor_id=str(current_user.id))

    # === Internal helpers ===

    @staticmethod
    def _assert_can_view(project: ApiProject, current_user: User) -> None:
        """Allow viewing only to owner or superuser (MVP)."""
        if current_user.is_superuser:
            return
        if project.owner_id == current_user.id:
            return
        raise ForbiddenException(
            "Only the project owner or an admin may access this project"
        )

    @staticmethod
    def _assert_can_modify(project: ApiProject, current_user: User) -> None:
        """Allow modification only to owner or superuser."""
        if current_user.is_superuser:
            return
        if project.owner_id == current_user.id:
            return
        raise ForbiddenException(
            "Only the project owner or an admin may modify this project"
        )