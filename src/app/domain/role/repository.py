"""Role repository for database operations."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.role.model import Role


class RoleRepository:
    """Role repository class."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID."""
        result = await self.session.execute(
            select(Role).where(Role.id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        result = await self.session.execute(
            select(Role).where(Role.name == name)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Role]:
        """Return all roles ordered by name."""
        result = await self.session.execute(
            select(Role).order_by(Role.name.asc())
        )
        return list(result.scalars().all())

    async def create(self, role: Role) -> Role:
        """Create a new role."""
        self.session.add(role)
        await self.session.flush()
        await self.session.refresh(role)
        return role

    async def update(self, role: Role) -> Role:
        """Update an existing role."""
        await self.session.flush()
        await self.session.refresh(role)
        return role

    async def delete(self, role: Role) -> None:
        """Delete a role."""
        await self.session.delete(role)
        await self.session.flush()
