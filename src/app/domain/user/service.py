"""User authentication service."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security import (
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
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
    UserWithTokenResponse,
)
from sqlalchemy import func, or_, select
from app.domain.user.schema import UserListResponse


class UserService:
    """User service for authentication and user management."""

    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)
        self.session = session

    async def register(self, request: UserRegisterRequest) -> UserWithTokenResponse:
        """Register a new user."""
        # Check if username or email already exists
        if await self.repository.get_by_email(request.email):
            raise ValueError("Email already registered")
        if await self.repository.get_by_username(request.username):
            raise ValueError("Username already taken")

        # Create new user
        user = User(
            username=request.username,
            email=request.email,
            hashed_password=hash_password(request.password),
            nickname=request.nickname,
            phone=request.phone,
        )
        user = await self.repository.create(user)
        await self.session.commit()

        # Generate tokens
        tokens = create_token_pair(user.id)

        return UserWithTokenResponse(
            user=UserResponse.model_validate(user),
            token=TokenResponse(**tokens),
        )

    async def login(self, request: UserLoginRequest) -> UserWithTokenResponse:
        """Login a user. Updates last_login_time as side-effect."""
        # Find user by email
        user = await self.repository.get_by_email(request.email)
        if not user:
            raise ValueError("Invalid email or password")

        # Verify password
        if not verify_password(request.password, user.hashed_password):
            raise ValueError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise ValueError("User account is disabled")

        # Update last_login_time
        user.last_login_time = datetime.now(timezone.utc)
        await self.repository.update(user)
        await self.session.commit()

        # Generate tokens
        tokens = create_token_pair(user.id)

        return UserWithTokenResponse(
            user=UserResponse.model_validate(user),
            token=TokenResponse(**tokens),
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        # Decode refresh token
        payload = decode_token(refresh_token)
        if not payload:
            raise ValueError("Invalid refresh token")

        # Check token type
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        # Get user from token subject
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload")

        # Verify user exists
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValueError("Invalid user id in token")

        user = await self.repository.get_by_id(user_uuid)
        if not user:
            raise ValueError("User not found")

        if not user.is_active:
            raise ValueError("User account is disabled")

        # Generate new token pair
        tokens = create_token_pair(user.id)

        return TokenResponse(**tokens)

    async def logout(self, access_token: str) -> LogoutResponse:
        """Logout a user by blacklisting the access token."""
        blacklist_token(access_token)
        return LogoutResponse()

    async def change_password(
        self,
        user_id: UUID,
        request: ChangePasswordRequest,
    ) -> None:
        """Change the current user's password."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Verify old password
        if not verify_password(request.old_password, user.hashed_password):
            raise ValueError("Incorrect old password")

        # Update password
        user.hashed_password = hash_password(request.new_password)
        await self.repository.update(user)
        await self.session.commit()

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return await self.repository.get_by_id(user_id)

    async def get_current_user(self, user_id: UUID) -> User:
        """Get current authenticated user."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if not user.is_active:
            raise ValueError("User account is disabled")
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

        # Total count
        count_stmt = select(func.count()).select_from(User)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Page items
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
        """Admin: update user attributes."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if request.nickname is not None:
            user.nickname = request.nickname
        if request.phone is not None:
            user.phone = request.phone
        if request.status is not None:
            user.status = request.status
        if request.role_id is not None:
            user.role_id = request.role_id
        if request.is_superuser is not None:
            user.is_superuser = request.is_superuser
        await self.repository.update(user)
        await self.session.commit()
        return UserResponse.model_validate(user)

    async def delete_user(self, user_id: UUID) -> None:
        """Soft-delete a user (status=0)."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if user.is_superuser:
            raise ValueError("Cannot delete superuser")
        user.status = 0
        await self.repository.update(user)
        await self.session.commit()
