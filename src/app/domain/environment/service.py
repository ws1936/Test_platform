"""Environment service for F005 — API testing environments.

Business rules implemented here:

* Every operation is **scoped to a project**; the service reuses
  :class:`ProjectService` to validate project existence and the
  caller's authorization (project owner or superuser). Non-owners
  get ``403 Forbidden``; missing projects get ``404`` — the same
  split used by F004 to avoid leaking project-ID existence.
* Environment names must be unique within a project
  (``ErrorCode 30008``, ``ConflictException``).
* At most one environment per project may carry ``is_default=True``
  (MODULE.md §5). The service guarantees this inside a single
  transaction: it demotes the previous default *before* promoting the
  new one. The Alembic partial unique index
  (``uq_api_environments_one_default_per_project``) is the database
  layer of defence; the service layer prevents the obvious race in
  application logic.
* Default environments cannot be hard-deleted
  (``ErrorCode 30009``). Callers must first promote another
  environment to default via :py:meth:`set_default_environment`.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    ConflictException,
    EnvironmentNotFoundException,
    ForbiddenException,
    ProjectNotFoundException,
)
from app.domain.environment.model import ApiEnvironment
from app.domain.environment.repository import EnvironmentRepository
from app.domain.environment.schema import (
    EnvironmentCreateRequest,
    EnvironmentListQuery,
    EnvironmentListResponse,
    EnvironmentResponse,
    EnvironmentUpdateRequest,
)
from app.domain.project.service import ProjectService
from app.domain.user.model import User


logger = logging.getLogger(__name__)


def _audit(
    event: str,
    *,
    environment_id: Optional[str] = None,
    project_id: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> None:
    """Emit a structured audit log line without leaking secrets.

    Matches the shape used by ``ProjectService._audit`` so log lines
    are easy to grep across features.
    """
    fields: dict[str, str] = {"event": event}
    if environment_id is not None:
        fields["environment_id"] = environment_id
    if project_id is not None:
        fields["project_id"] = project_id
    if actor_id is not None:
        fields["actor_id"] = actor_id
    logger.info("environment.audit %s", fields)


class EnvironmentService:
    """Environment business logic for F005."""

    def __init__(self, session: AsyncSession):
        self.repository = EnvironmentRepository(session)
        self.project_service = ProjectService(session)
        self.session = session

    # === Helpers ===

    async def _load_project_for_user(
        self,
        project_id: UUID,
        *,
        current_user: User,
        for_modify: bool,
    ) -> None:
        """Confirm the project exists and the caller may access it.

        Delegates to :py:meth:`ProjectService.get_project` so the
        same 404-vs-403 split and "owner or superuser" rule used by
        F004 also applies to F005.

        Args:
            current_user: authenticated user (keyword-only).
            for_modify: if ``True``, an additional owner / admin
                check is applied before mutating operations.
        """
        try:
            project = await self.project_service.get_project(
                project_id, current_user=current_user
            )
        except ProjectNotFoundException as exc:
            # Re-raise with a feature-appropriate message; the
            # status_code (404) and code (PROJECT_NOT_FOUND) are kept.
            raise ProjectNotFoundException() from exc

        if for_modify and not (
            current_user.is_superuser or project.owner_id == current_user.id
        ):
            raise ForbiddenException(
                "Only the project owner or an admin may modify this project"
            )

    # === Create ===

    async def create_environment(
        self,
        project_id: UUID,
        request: EnvironmentCreateRequest,
        *,
        current_user: User,
    ) -> EnvironmentResponse:
        """Create a new environment under ``project_id``.

        Authorization: project owner or superuser.
        """
        await self._load_project_for_user(
            project_id, current_user=current_user, for_modify=True
        )

        # Uniqueness check (defence in depth — the partial unique
        # index is the authoritative source of truth).
        existing = await self.repository.get_by_project_and_name(
            project_id=project_id, name=request.name
        )
        if existing is not None:
            raise ConflictException(
                message=f"Environment name '{request.name}' already exists "
                "in this project",
                details={"code": "ENVIRONMENT_NAME_TAKEN"},
            )

        # Promote default inside the same transaction so concurrent
        # requests cannot observe two ``is_default=True`` rows.
        env = ApiEnvironment(
            project_id=project_id,
            name=request.name,
            base_url=request.base_url,
            headers=request.headers,
            variables=request.variables,
            is_default=request.is_default,
        )
        env = await self.repository.create(env)
        if env.is_default:
            await self.repository.clear_default_in_project(
                project_id=project_id, except_id=env.id
            )
            await self.session.flush()

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            # The partial unique index fired — surface as the same
            # conflict the pre-check would have produced.
            raise ConflictException(
                message=f"Environment name '{request.name}' already exists "
                "in this project",
                details={"code": "ENVIRONMENT_NAME_TAKEN"},
            ) from exc

        _audit(
            "create",
            environment_id=str(env.id),
            project_id=str(project_id),
            actor_id=str(current_user.id),
        )
        return EnvironmentResponse.model_validate(env)

    # === Read ===

    async def get_environment(
        self,
        environment_id: UUID,
        *,
        current_user: User,
    ) -> ApiEnvironment:
        """Fetch an environment by ID and verify project access.

        Authorization: project owner or superuser. Non-owners get
        ``403 Forbidden``; missing environments get ``404``.

        Raises:
            EnvironmentNotFoundException: when the environment does
                not exist.
            ForbiddenException: when the caller is neither project
                owner nor admin.
        """
        env = await self.repository.get_by_id(environment_id)
        if env is None:
            raise EnvironmentNotFoundException()
        await self._load_project_for_user(
            env.project_id, current_user=current_user, for_modify=False
        )
        return env

    async def list_environments(
        self,
        project_id: UUID,
        query: EnvironmentListQuery,
        *,
        current_user: User,
    ) -> EnvironmentListResponse:
        """List environments of a project (view-level access)."""
        await self._load_project_for_user(
            project_id, current_user=current_user, for_modify=False
        )

        items, total = await self.repository.list_by_project(
            project_id=project_id,
            search=query.search,
        )
        return EnvironmentListResponse(
            items=[EnvironmentResponse.model_validate(e) for e in items],
            total=total,
        )

    # === Update ===

    async def update_environment(
        self,
        environment_id: UUID,
        request: EnvironmentUpdateRequest,
        *,
        current_user: User,
    ) -> EnvironmentResponse:
        """Update an environment (name / base_url / headers / variables / is_default).

        Authorization: project owner or superuser.

        Uniqueness and "single default" rules are re-enforced inside
        the transaction so concurrent edits cannot break them.
        """
        env = await self.repository.get_by_id(environment_id)
        if env is None:
            raise EnvironmentNotFoundException()
        await self._load_project_for_user(
            env.project_id, current_user=current_user, for_modify=True
        )

        # --- name change → uniqueness check ---
        if request.name is not None and request.name != env.name:
            clash = await self.repository.get_by_project_and_name(
                project_id=env.project_id, name=request.name
            )
            if clash is not None and clash.id != env.id:
                raise ConflictException(
                    message=f"Environment name '{request.name}' already exists "
                    "in this project",
                    details={"code": "ENVIRONMENT_NAME_TAKEN"},
                )
            env.name = request.name

        # --- scalar fields ---
        if request.base_url is not None:
            env.base_url = request.base_url
        if request.headers is not None:
            env.headers = request.headers
        if request.variables is not None:
            env.variables = request.variables

        # --- default promotion ---
        became_default = (
            request.is_default is True and env.is_default is False
        )
        if became_default:
            await self.repository.clear_default_in_project(
                project_id=env.project_id, except_id=env.id
            )
            env.is_default = True
        # ``is_default`` flips from True → False are not supported via
        # PUT for MVP (callers use ``DELETE /environments/{id}/default``
        # in the planned enhancement). Silently ignoring the False
        # flip avoids accidentally removing the only default.

        env = await self.repository.update(env)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException(
                message=f"Environment name '{request.name or env.name}' "
                "already exists in this project",
                details={"code": "ENVIRONMENT_NAME_TAKEN"},
            ) from exc

        _audit(
            "update",
            environment_id=str(env.id),
            project_id=str(env.project_id),
            actor_id=str(current_user.id),
        )
        return EnvironmentResponse.model_validate(env)

    # === Delete ===

    async def delete_environment(
        self,
        environment_id: UUID,
        *,
        current_user: User,
    ) -> None:
        """Hard-delete an environment.

        Authorization: project owner or superuser.

        Default environments **cannot** be deleted — callers must
        first promote another environment via
        :py:meth:`set_default_environment`. This keeps the project
        from entering a "no default environment" state that would
        later break execution (MODULE.md §5).
        """
        env = await self.repository.get_by_id(environment_id)
        if env is None:
            raise EnvironmentNotFoundException()
        await self._load_project_for_user(
            env.project_id, current_user=current_user, for_modify=True
        )

        if env.is_default:
            raise ConflictException(
                message=(
                    "Default environment cannot be deleted. Promote another "
                    "environment to default first."
                ),
                details={"code": "ENVIRONMENT_DEFAULT_NOT_DELETABLE"},
            )

        await self.repository.delete(env)
        await self.session.commit()
        _audit(
            "delete",
            environment_id=str(environment_id),
            project_id=str(env.project_id),
            actor_id=str(current_user.id),
        )

    # === Default management ===

    async def set_default_environment(
        self,
        environment_id: UUID,
        *,
        current_user: User,
    ) -> EnvironmentResponse:
        """Promote an environment to the project's default.

        Authorization: project owner or superuser.

        The previous default (if any) is demoted inside the same
        transaction so we never expose two ``is_default=True`` rows.
        """
        env = await self.repository.get_by_id(environment_id)
        if env is None:
            raise EnvironmentNotFoundException()
        await self._load_project_for_user(
            env.project_id, current_user=current_user, for_modify=True
        )

        if not env.is_default:
            await self.repository.clear_default_in_project(
                project_id=env.project_id, except_id=env.id
            )
            env.is_default = True
            env = await self.repository.update(env)
            await self.session.commit()
            _audit(
                "set_default",
                environment_id=str(env.id),
                project_id=str(env.project_id),
                actor_id=str(current_user.id),
            )

        return EnvironmentResponse.model_validate(env)
