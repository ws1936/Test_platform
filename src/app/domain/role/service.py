"""Role service for RBAC operations."""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.role.model import Role
from app.domain.role.repository import RoleRepository
from app.domain.role.schema import RoleCreateRequest, RoleUpdateRequest


class RoleService:
    """Role service."""

    def __init__(self, session: AsyncSession):
        self.repository = RoleRepository(session)
        self.session = session

    async def list_roles(self) -> list[Role]:
        return await self.repository.list_all()

    async def get_role(self, role_id: UUID) -> Optional[Role]:
        return await self.repository.get_by_id(role_id)

    async def create_role(self, request: RoleCreateRequest) -> Role:
        if await self.repository.get_by_name(request.name):
            raise ValueError(f"Role '{request.name}' already exists")
        role = Role(
            name=request.name,
            description=request.description,
            permissions=request.permissions,
        )
        role = await self.repository.create(role)
        await self.session.commit()
        return role

    async def update_role(
        self,
        role_id: UUID,
        request: RoleUpdateRequest,
    ) -> Role:
        role = await self.repository.get_by_id(role_id)
        if not role:
            raise ValueError("Role not found")
        if request.name is not None and request.name != role.name:
            if await self.repository.get_by_name(request.name):
                raise ValueError(f"Role '{request.name}' already exists")
            role.name = request.name
        if request.description is not None:
            role.description = request.description
        if request.permissions is not None:
            role.permissions = request.permissions
        role = await self.repository.update(role)
        await self.session.commit()
        return role

    async def delete_role(self, role_id: UUID) -> None:
        role = await self.repository.get_by_id(role_id)
        if not role:
            raise ValueError("Role not found")
        if role.is_system:
            raise ValueError("System role cannot be deleted")
        await self.repository.delete(role)
        await self.session.commit()
