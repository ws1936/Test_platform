"""Project repository for database operations.

Thin wrapper around SQLAlchemy; the service layer owns business rules
(ownership / admin authorization). Mirrors the style of
``UserRepository`` / ``RoleRepository``.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.project.model import ApiProject


class ProjectRepository:
    """Project repository class."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, project_id: UUID) -> Optional[ApiProject]:
        """Get a project by ID."""
        result = await self.session.execute(
            select(ApiProject).where(ApiProject.id == project_id)
        )
        return result.scalar_one_or_none()

    async def create(self, project: ApiProject) -> ApiProject:
        """Create a new project and refresh to load server defaults."""
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def update(self, project: ApiProject) -> ApiProject:
        """Flush pending changes and refresh server-side values."""
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def delete(self, project: ApiProject) -> None:
        """Hard-delete a project (no soft delete in MVP)."""
        await self.session.delete(project)
        await self.session.flush()

    async def list_paginated(
        self,
        *,
        page: int,
        size: int,
        search: Optional[str] = None,
        owner_id: Optional[UUID] = None,
    ) -> tuple[list[ApiProject], int]:
        """List projects with optional name search and owner filter.

        Returns ``(items, total)``. ``total`` is the count *after*
        applying the same filters so the UI can render correct page
        counts.
        """
        conditions = []
        if search:
            like = f"%{search}%"
            conditions.append(ApiProject.name.ilike(like))
        if owner_id is not None:
            conditions.append(ApiProject.owner_id == owner_id)

        # --- total ---
        count_stmt = select(func.count()).select_from(ApiProject)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        # --- page ---
        offset = (page - 1) * size
        list_stmt = select(ApiProject).order_by(ApiProject.created_at.desc())
        if conditions:
            list_stmt = list_stmt.where(*conditions)
        list_stmt = list_stmt.offset(offset).limit(size)
        result = await self.session.execute(list_stmt)
        items = list(result.scalars().all())

        return items, int(total)