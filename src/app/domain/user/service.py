"""User authentication & management service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    AccountDisabledException,
    CredentialsInvalidException,
    EmailAlreadyExistsException,
    IncorrectOldPasswordException,
    TokenInvalidException,
    UsernameAlreadyExistsException,
    UserNotFoundException,
)
from app.common.security import (
    TokenError,
    blacklist_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.user.model import User
from app.domain.user.repository import UserRepository
from app.domain.user.schema import (
    ChangePasswordRequest,
    LogoutResponse,
    TokenResponse,
    UserListQuery,
    UserLoginRequest,
    UserPublicResponse,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
    UserWithTokenResponse,
)
from app.domain.user.schema import UserListResponse


logger = logging.getLogger(__name__)


def _audit(event: str, *, user_id: Optional[str] = None, email: Optional[str] = None) -> None:
    """Emit a structured-ish audit log line without leaking secrets."""
    fields = {"event": event}
    if user_id is not None:
        fields["user_id"] = user_id
    if email is not None:
        fields["email"] = email
    logger.info("auth.audit %s", fields)


class UserService:
    """User service for authentication and user management."""

    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)
        self.session = session

    # === Authentication ===

    async def register(
        self,
        request: UserRegisterRequest,
        *,
        is_first_user: bool = False,
    ) -> UserWithTokenResponse:
        """Register a new user.

        The very first registered user is automatically promoted to
        superuser so the platform has an admin bootstrap (Review M-R1).
        Every subsequent registration is gated by the router, which
        enforces an existing superuser token before calling this method.

        Raises:
            EmailAlreadyExistsException: when email is taken (409).
            UsernameAlreadyExistsException: when username is taken (409).
        """
        existing_email = await self.repository.get_by_email(request.email)
        if existing_email is not None:
            _audit("register.email_conflict", email=request.email)
            raise EmailAlreadyExistsException()

        existing_username = await self.repository.get_by_username(request.username)
        if existing_username is not None:
            _audit("register.username_conflict", email=request.email)
            raise UsernameAlreadyExistsException()

        user = User(
            username=request.username,
            email=request.email,
            hashed_password=hash_password(request.password),
            nickname=request.nickname,
            phone=request.phone,
            is_superuser=bool(is_first_user),
        )
        user = await self.repository.create(user)
        await self.session.commit()

        tokens = create_token_pair(user.id, token_version=user.token_version)
        _audit(
            "register.success",
            user_id=str(user.id),
            email=user.email,
        )

        return UserWithTokenResponse(
            user=UserPublicResponse.model_validate(user),
            token=TokenResponse(**tokens),
        )

    async def count_users(self) -> int:
        """Return the total number of users (for bootstrap decisions)."""
        from sqlalchemy import func as _func, select as _select

        result = await self.session.execute(
            _select(_func.count()).select_from(User)
        )
        return int(result.scalar_one())

    async def login(self, request: UserLoginRequest) -> UserWithTokenResponse:
        """Authenticate a user by email + password.

        Returns a fresh access/refresh token pair. Bumps
        ``last_login_time`` on success.

        Raises:
            CredentialsInvalidException: email unknown or password wrong (401).
            AccountDisabledException: account is disabled (403).
        """
        user = await self.repository.get_by_email(request.email)
        if user is None or not verify_password(request.password, user.hashed_password):
            # Identical message for both cases to avoid user enumeration.
            _audit("login.failed", email=request.email)
            raise CredentialsInvalidException()

        if not user.is_active:
            _audit("login.disabled", user_id=str(user.id), email=user.email)
            raise AccountDisabledException()

        user.last_login_time = datetime.now(timezone.utc)
        await self.repository.update(user)
        await self.session.commit()

        tokens = create_token_pair(user.id, token_version=user.token_version)
        _audit("login.success", user_id=str(user.id), email=user.email)

        return UserWithTokenResponse(
            user=UserPublicResponse.model_validate(user),
            token=TokenResponse(**tokens),
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Exchange a valid refresh token for a new access/refresh pair."""
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except TokenError as exc:
            _audit("refresh.invalid_token")
            raise TokenInvalidException("Invalid refresh token") from exc

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise TokenInvalidException("Invalid refresh token payload")
        try:
            user_uuid = UUID(user_id_str)
        except (TypeError, ValueError) as exc:
            raise TokenInvalidException("Invalid refresh token subject") from exc

        user = await self.repository.get_by_id(user_uuid)
        if user is None:
            raise UserNotFoundException()

        if not user.is_active:
            raise AccountDisabledException()

        # Bind the new token to the user's current credential version so
        # password changes invalidate outstanding refresh tokens.
        if int(payload.get("v", 0)) != user.token_version:
            raise TokenInvalidException("Refresh token has been revoked")

        tokens = create_token_pair(user.id, token_version=user.token_version)
        _audit("refresh.success", user_id=str(user.id))
        return TokenResponse(**tokens)

    async def logout(self, access_token: str) -> LogoutResponse:
        """Revoke the supplied access token via the blacklist."""
        blacklist_token(access_token)
        _audit("logout.success")
        return LogoutResponse()

    async def bump_token_version(self, user_id: UUID) -> None:
        """Bump ``token_version`` so previously issued access tokens are
        rejected by ``get_current_user_with_version``.

        This is a test/back-office helper — production code does not need
        a public mutation; it already happens in :meth:`change_password`
        and the user disable flow.  Exposed for tests that need to
        exercise the "stale access token" contract.
        """
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundException()
        user.token_version = user.token_version + 1
        await self.repository.update(user)
        await self.session.commit()
        _audit("token_version.bump", user_id=str(user.id))

    async def change_password(
        self,
        user_id: UUID,
        request: ChangePasswordRequest,
    ) -> None:
        """Change the current user's password.

        On success, ``token_version`` is incremented so all previously
        issued JWTs become invalid on their next use.
        """
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundException()

        if not verify_password(request.old_password, user.hashed_password):
            _audit("password_change.bad_old", user_id=str(user.id))
            raise IncorrectOldPasswordException()

        user.hashed_password = hash_password(request.new_password)
        user.token_version = user.token_version + 1
        await self.repository.update(user)
        await self.session.commit()
        _audit("password_change.success", user_id=str(user.id))

    # === User lookup ===

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return await self.repository.get_by_id(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Look up a user by email (used by the registration gate)."""
        return await self.repository.get_by_email(email)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Look up a user by username (used by the registration gate)."""
        return await self.repository.get_by_username(username)

    async def get_current_user(self, user_id: UUID) -> User:
        """Get the current authenticated user.

        Raises:
            UserNotFoundException: when the user no longer exists.
            AccountDisabledException: when the account is disabled.
        """
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundException()
        if not user.is_active:
            raise AccountDisabledException()
        return user

    # === User management (admin) ===

    async def list_users(self, query: UserListQuery) -> UserListResponse:
        """Paginated user list with optional search."""
        conditions = []
        if query.search:
            like = f"%{query.search}%"
            conditions.append(
                or_(
                    User.email.ilike(like),
                    User.username.ilike(like),
                    User.nickname.ilike(like),
                )
            )

        count_stmt = select(func.count()).select_from(User)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (query.page - 1) * query.size
        list_stmt = select(User).order_by(User.created_at.desc())
        if conditions:
            list_stmt = list_stmt.where(*conditions)
        list_stmt = list_stmt.offset(offset).limit(query.size)
        result = await self.session.execute(list_stmt)
        users = list(result.scalars().all())

        return UserListResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=query.page,
            size=query.size,
        )

    async def update_user(
        self,
        user_id: UUID,
        request: UserUpdateRequest,
    ) -> UserResponse:
        """Admin: update user attributes.

        Bumping ``status`` from 1 -> 0 (disabling) also bumps
        ``token_version`` so outstanding JWTs cannot keep using the
        account.
        """
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundException()
        if request.nickname is not None:
            user.nickname = request.nickname
        if request.phone is not None:
            user.phone = request.phone
        status_changed_to_disabled = (
            request.status is not None and request.status == 0 and user.status != 0
        )
        if request.status is not None:
            user.status = request.status
        if request.role_id is not None:
            user.role_id = request.role_id
        if request.is_superuser is not None:
            user.is_superuser = request.is_superuser
        if status_changed_to_disabled:
            user.token_version = user.token_version + 1
        await self.repository.update(user)
        await self.session.commit()
        return UserResponse.model_validate(user)

    async def delete_user(self, user_id: UUID) -> None:
        """Soft-delete a user (status=0). Bumps ``token_version``."""
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundException()
        if user.is_superuser:
            # Use a generic business exception; the router maps it to 400.
            from app.common.exceptions import BadRequestException

            raise BadRequestException("Cannot delete a superuser")
        user.status = 0
        user.token_version = user.token_version + 1
        await self.repository.update(user)
        await self.session.commit()