from uuid import UUID

from fastapi import Depends

from src.api.v1.features.users import schemas as user_schemas
from src.api.v1.features.users.user_repo import UserRepo, get_user_repo
from src.core.security.authentication import hash_password, verify_password
from src.api.v1.shared.enums import RoleName, UserStatus
from src.utils.exeptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class UserService:
    def __init__(self, user_repo: UserRepo):
        self.user_repo = user_repo

    @staticmethod
    def _to_read(user) -> user_schemas.UserRead:
        return user_schemas.UserRead.model_validate(user)

    async def email_exists(self, email: str) -> bool:
        return await self.user_repo.email_exists(email)

    async def create_user(
        self, email: str, password_hash: str, role_name: RoleName, status: UserStatus
    ) -> user_schemas.UserRead:
        if await self.email_exists(email=email):
            raise ConflictException("Email already exists")

        user = await self.user_repo.create_user(
            email=email,
            password_hash=password_hash,
            role_name=role_name,
            status=status,
        )
        return self._to_read(user)

    async def get_user(self, user_id: UUID) -> user_schemas.UserRead:
        user = await self.user_repo.get_user_by_id(user_id)
        if user is None:
            logger.warning("Get user not found: user_id=%s", user_id)
            raise NotFoundException("User")
        return self._to_read(user)

    async def list_users(
        self,
        query: user_schemas.UserListQuery,
    ) -> dict:
        users, total = await self.user_repo.list_users(
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            status=query.status,
            role=query.role,
        )
        logger.info(
            "List users: page=%s page_size=%s total=%s search=%s status=%s role=%s",
            query.page,
            query.page_size,
            total,
            query.search,
            query.status,
            query.role,
        )
        return {
            "items": [self._to_read(user) for user in users],
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
        }

    @staticmethod
    def _ensure_can_update_profile(actor, target) -> None:
        if actor.user_id == target.user_id or actor.role_name == RoleName.admin:
            return
        if actor.role_name == RoleName.hr and target.role_name in {
            RoleName.manager,
            RoleName.employee,
        }:
            return
        raise ForbiddenException("cannot_manage_equal_or_higher_role")

    @staticmethod
    def _ensure_admin(actor) -> None:
        if actor.role_name != RoleName.admin:
            raise ForbiddenException("Only an administrator can perform this action")

    async def _get_locked_user(self, user_id: UUID):
        user = await self.user_repo.get_user_for_update(user_id)
        if user is None:
            raise NotFoundException("User")
        return user

    @staticmethod
    def _ensure_not_last_active_admin(
        target,
        active_admin_ids: list[UUID],
        *,
        next_role: RoleName | None = None,
        next_status: UserStatus | None = None,
    ) -> None:
        removes_active_admin = (
            target.role_name == RoleName.admin
            and target.status == UserStatus.active
            and (
                (next_role is not None and next_role != RoleName.admin)
                or (next_status is not None and next_status != UserStatus.active)
            )
        )
        if removes_active_admin and len(active_admin_ids) <= 1:
            raise ConflictException("The last active administrator cannot be changed")

    async def update_profile(
        self,
        user_id: UUID,
        payload: user_schemas.UserProfileUpdate,
        actor,
    ) -> user_schemas.UserRead:
        target = await self.user_repo.get_user_or_404(user_id)
        self._ensure_can_update_profile(actor, target)
        user = await self.user_repo.update_profile(user_id=user_id, email=payload.email)
        logger.info(
            "User profile updated: user_id=%s actor_id=%s", user_id, actor.user_id
        )
        return self._to_read(user)

    async def change_password(
        self,
        user_id: UUID,
        payload: user_schemas.ChangePasswordRequest,
        actor,
    ) -> user_schemas.UserRead:
        if actor.user_id != user_id:
            raise ForbiddenException("You can only change your own password")

        existing_user = await self.user_repo.get_user_for_update(user_id)
        if existing_user is None:
            logger.warning("Change password user not found: user_id=%s", user_id)
            raise NotFoundException("User")

        if not verify_password(payload.old_password, existing_user.password_hash):
            logger.warning(
                "Change password rejected: wrong current password user_id=%s", user_id
            )
            raise BadRequestException("Current password is incorrect")

        new_hash = hash_password(payload.new_password)
        updated_user = await self.user_repo.apply_security_update(
            existing_user,
            password_hash=new_hash,
        )
        logger.info("Password changed: user_id=%s", user_id)
        return self._to_read(updated_user)

    async def admin_reset_password(
        self,
        user_id: UUID,
        payload: user_schemas.AdminPasswordReset,
        actor,
    ) -> user_schemas.UserRead:
        self._ensure_admin(actor)
        if actor.user_id == user_id:
            raise ForbiddenException("Use the self-service password change endpoint")
        target = await self._get_locked_user(user_id)
        updated = await self.user_repo.apply_security_update(
            target,
            password_hash=hash_password(payload.new_password),
        )
        logger.info(
            "Password reset by admin: user_id=%s actor_id=%s", user_id, actor.user_id
        )
        return self._to_read(updated)

    async def assign_role(
        self,
        user_id: UUID,
        payload: user_schemas.RoleAssignmentRequest,
        actor,
    ) -> user_schemas.UserRead:
        self._ensure_admin(actor)
        if actor.user_id == user_id:
            raise ForbiddenException("Users cannot change their own role")

        active_admin_ids = await self.user_repo.lock_active_admin_ids()
        target = await self._get_locked_user(user_id)
        self._ensure_not_last_active_admin(
            target,
            active_admin_ids,
            next_role=payload.role_name,
        )
        user = await self.user_repo.apply_security_update(
            target,
            role_name=payload.role_name,
        )
        logger.info("Role assigned: user_id=%s role=%s", user_id, payload.role_name)
        return self._to_read(user)

    async def update_status(
        self,
        user_id: UUID,
        payload: user_schemas.UserStatusUpdate,
        actor,
    ) -> user_schemas.UserRead:
        self._ensure_admin(actor)
        if actor.user_id == user_id and payload.status != UserStatus.active:
            raise ForbiddenException("Administrators cannot disable their own account")

        active_admin_ids = await self.user_repo.lock_active_admin_ids()
        target = await self._get_locked_user(user_id)
        self._ensure_not_last_active_admin(
            target,
            active_admin_ids,
            next_status=payload.status,
        )
        user = await self.user_repo.apply_security_update(target, status=payload.status)
        logger.info(
            "User status updated: user_id=%s status=%s actor_id=%s",
            user_id,
            payload.status,
            actor.user_id,
        )
        return self._to_read(user)

    async def deactivate_user(self, user_id: UUID, actor) -> user_schemas.UserRead:
        return await self.update_status(
            user_id,
            user_schemas.UserStatusUpdate(status=UserStatus.inactive),
            actor,
        )

    async def delete_user(self, user_id: UUID) -> None:
        deleted = await self.user_repo.delete_user(user_id)
        if not deleted:
            logger.warning("Delete user not found: user_id=%s", user_id)
            raise NotFoundException("User")
        logger.info("User deleted: user_id=%s", user_id)


def get_user_service(
    user_repo: UserRepo = Depends(get_user_repo),
) -> UserService:
    return UserService(user_repo=user_repo)
