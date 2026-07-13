"""Environment repository for F005 — database operations.

Thin wrapper around SQLAlchemy; the service layer owns business rules
(unique name per project, single default environment, project
authorization). Mirrors the style of ``ProjectRepository`` /
``UserRepository``.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.environment.model import ApiEnvironment


class EnvironmentRepository:
    """Environment repository class."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # === Single-row reads ===

    async def get_by_id(self, environment_id: UUID) -> Optional[ApiEnvironment]:
        """Get an environment by ID."""
        result = await self.session.execute(
            select(ApiEnvironment).where(ApiEnvironment.id == environment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_project_and_name(
        self,
        *,
        project_id: UUID,
        name: str,
    ) -> Optional[ApiEnvironment]:
        """Get an environment by ``(project_id, name)``.

        Used to enforce the per-project uniqueness rule (MODULE.md §5).
        """
        result = await self.session.execute(
            select(ApiEnvironment).where(
                ApiEnvironment.project_id == project_id,
                ApiEnvironment.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def get_default_by_project(
        self, project_id: UUID
    ) -> Optional[ApiEnvironment]:
        """Get the default environment of a project (or ``None``).

        Reads the most recently created ``is_default=True`` row so a
        stale duplicate (which the unique index should prevent but we
        still guard against) does not return multiple rows.
        """
        result = await self.session.execute(
            select(ApiEnvironment)
            .where(
                ApiEnvironment.project_id == project_id,
                ApiEnvironment.is_default.is_(True),
            )
            .order_by(ApiEnvironment.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # === Writes ===

    async def create(self, environment: ApiEnvironment) -> ApiEnvironment:
        """Create a new environment and refresh to load server defaults."""
        self.session.add(environment)
        await self.session.flush()
        await self.session.refresh(environment)
        return environment

    async def update(self, environment: ApiEnvironment) -> ApiEnvironment:
        """Flush pending changes and refresh server-side values."""
        await self.session.flush()
        await self.session.refresh(environment)
        return environment

    async def delete(self, environment: ApiEnvironment) -> None:
        """Hard-delete an environment (no soft delete in MVP)."""
        await self.session.delete(environment)
        await self.session.flush()

    async def clear_default_in_project(
        self,
        *,
        project_id: UUID,
        except_id: Optional[UUID] = None,
    ) -> int:
        """Reset ``is_default=False`` for every other env in a project.

        Used by :class:`EnvironmentService` to enforce "at most one
        default environment per project" (MODULE.md §5). Runs as a
        single ``UPDATE`` so we never read-then-write individual rows
        from inside the service transaction.

        Args:
            project_id: target project.
            except_id: environment ID to skip (typically the one being
                promoted to default in the same transaction).

        Returns:
            Number of rows updated (used by tests / audit logs).
        """
        stmt = (
            update(ApiEnvironment)
            .where(
                ApiEnvironment.project_id == project_id,
                ApiEnvironment.is_default.is_(True),
            )
            .values(is_default=False)
        )
        if except_id is not None:
            stmt = stmt.where(ApiEnvironment.id != except_id)
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    # === List ===

    async def list_by_project(
        self,
        *,
        project_id: UUID,
        search: Optional[str] = None,
    ) -> tuple[list[ApiEnvironment], int]:
        """List environments of a project with optional name search.

        Returns ``(items, total)``. ``total`` is computed *after*
        applying the search filter so the UI can render an accurate
        count. Default environments sort first, then everything else
        by creation time.
        """
        conditions = [ApiEnvironment.project_id == project_id]
        if search:
            like = f"%{search}%"
            conditions.append(ApiEnvironment.name.ilike(like))

        # --- total ---
        count_stmt = select(func.count()).select_from(ApiEnvironment)
        count_stmt = count_stmt.where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        # --- page ---
        list_stmt = select(ApiEnvironment).where(*conditions)
        # ``is_default DESC`` puts True (1) before False (0) on both
        # PostgreSQL and SQLite so the default environment always
        # shows up at the top of the list.
        list_stmt = list_stmt.order_by(
            ApiEnvironment.is_default.desc(),
            ApiEnvironment.created_at.asc(),
        )
        result = await self.session.execute(list_stmt)
        items = list(result.scalars().all())

        return items, int(total)
