from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from src.api.v1.features.auth import schemas as auth_schemas
from src.api.v1.features.auth.auth_repo import AuthRepo
from src.api.v1.features.auth.service import AuthService
from src.api.v1.features.users import schemas
from src.api.v1.features.users.service import UserService
from src.api.v1.features.users.user_repo import UserRepo
from src.api.v1.shared.enums import RoleName, UserStatus
from src.core.dependencies.auth import get_current_user
from src.core.exceptions import (
    ConflictException,
    ForbiddenException,
    UnauthorizedException,
)
from src.core.security.authentication import create_access_token, hash_password


def make_user(role_name: RoleName, *, password: str = "Current123"):
    now = datetime.now(timezone.utc)
    role = SimpleNamespace(
        role_id=list(RoleName).index(role_name) + 1,
        name=role_name,
        description=None,
        created_at=now,
        updated_at=now,
    )
    return SimpleNamespace(
        user_id=uuid.uuid4(),
        email=f"{role_name.value}-{uuid.uuid4().hex[:8]}@example.test",
        password_hash=hash_password(password),
        role_id=role.role_id,
        role=role,
        role_name=role_name,
        status=UserStatus.active,
        token_version=0,
        refresh_token_hash="existing-refresh-hash",
        refresh_token_expires_at=now,
        refresh_token_created_at=now,
        last_login_at=None,
        created_at=now,
        updated_at=now,
    )


class FakeUserRepo:
    def __init__(self, *users) -> None:
        self.users = {user.user_id: user for user in users}

    async def get_user_or_404(self, user_id):
        return self.users[user_id]

    async def get_user_for_update(self, user_id):
        return self.users.get(user_id)

    async def lock_active_admin_ids(self):
        return [
            user.user_id
            for user in self.users.values()
            if user.role_name == RoleName.admin and user.status == UserStatus.active
        ]

    async def apply_security_update(
        self,
        user,
        *,
        password_hash=None,
        role_name=None,
        status=None,
    ):
        changed = False
        if password_hash is not None:
            user.password_hash = password_hash
            changed = True
        if role_name is not None and role_name != user.role_name:
            user.role_name = role_name
            user.role.name = role_name
            changed = True
        if status is not None and status != user.status:
            user.status = status
            changed = True
        if changed:
            user.token_version += 1
            user.refresh_token_hash = None
            user.refresh_token_expires_at = None
            user.refresh_token_created_at = None
        return user


class RefreshAwareAuthRepo:
    def __init__(self, user, refresh_token: str) -> None:
        self.user = user
        self.refresh_token = refresh_token

    async def get_user_by_refresh_token(self, refresh_token: str):
        if self.user.refresh_token_hash is None:
            return None
        if refresh_token == self.refresh_token:
            return self.user
        return None


class FakeResult:
    def __init__(self, user) -> None:
        self.user = user

    def scalar_one_or_none(self):
        return self.user


class FakeDB:
    def __init__(self, user) -> None:
        self.user = user

    async def execute(self, _statement):
        return FakeResult(self.user)


def make_service(*users) -> UserService:
    return UserService(cast(UserRepo, FakeUserRepo(*users)))


def test_hr_cannot_assign_admin_to_self() -> None:
    hr = make_user(RoleName.hr)
    service = make_service(hr)

    with pytest.raises(ForbiddenException):
        asyncio.run(
            service.assign_role(
                hr.user_id,
                schemas.RoleAssignmentRequest(role_name=RoleName.admin),
                hr,
            )
        )


def test_hr_cannot_assign_admin_to_another_employee() -> None:
    hr = make_user(RoleName.hr)
    employee = make_user(RoleName.employee)
    service = make_service(hr, employee)

    with pytest.raises(ForbiddenException):
        asyncio.run(
            service.assign_role(
                employee.user_id,
                schemas.RoleAssignmentRequest(role_name=RoleName.admin),
                hr,
            )
        )


def test_hr_cannot_reset_admin_password() -> None:
    hr = make_user(RoleName.hr)
    admin = make_user(RoleName.admin)
    service = make_service(hr, admin)

    with pytest.raises(ForbiddenException):
        asyncio.run(
            service.admin_reset_password(
                admin.user_id,
                schemas.AdminPasswordReset(new_password="Replacement123"),
                hr,
            )
        )


def test_employee_cannot_change_own_role() -> None:
    employee = make_user(RoleName.employee)
    service = make_service(employee)

    with pytest.raises(ForbiddenException):
        asyncio.run(
            service.assign_role(
                employee.user_id,
                schemas.RoleAssignmentRequest(role_name=RoleName.admin),
                employee,
            )
        )


def test_admin_role_assignment_revokes_existing_session() -> None:
    admin = make_user(RoleName.admin)
    employee = make_user(RoleName.employee)
    old_refresh_token = "old-refresh-token-value"
    service = make_service(admin, employee)

    updated = asyncio.run(
        service.assign_role(
            employee.user_id,
            schemas.RoleAssignmentRequest(role_name=RoleName.manager),
            admin,
        )
    )

    assert updated.role_name == RoleName.manager
    assert employee.token_version == 1
    assert employee.refresh_token_hash is None

    auth_service = AuthService(
        cast(AuthRepo, RefreshAwareAuthRepo(employee, old_refresh_token)),
        cast(object, SimpleNamespace()),
    )
    with pytest.raises(UnauthorizedException):
        asyncio.run(
            auth_service.refresh(
                auth_schemas.RefreshTokenRequest(refresh_token=old_refresh_token)
            )
        )


def test_old_access_token_is_invalid_after_password_change() -> None:
    employee = make_user(RoleName.employee)
    service = make_service(employee)
    old_access_token, _, _ = create_access_token(
        user_id=str(employee.user_id),
        role=employee.role_name.value,
        token_version=employee.token_version,
    )

    asyncio.run(
        service.change_password(
            employee.user_id,
            schemas.ChangePasswordRequest(
                old_password="Current123",
                new_password="Replacement123",
            ),
            employee,
        )
    )

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=None)))
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=old_access_token,
    )
    with pytest.raises(UnauthorizedException):
        asyncio.run(
            get_current_user(
                request=cast(object, request),
                credentials=credentials,
                db=cast(object, FakeDB(employee)),
            )
        )


def test_last_active_admin_cannot_be_demoted() -> None:
    admin = make_user(RoleName.admin)
    service = make_service(admin)

    # A different admin actor avoids the self-role guard and exercises last-admin logic.
    actor = make_user(RoleName.admin)
    cast(FakeUserRepo, service.user_repo).users[actor.user_id] = actor
    actor.status = UserStatus.inactive

    with pytest.raises(ConflictException):
        asyncio.run(
            service.assign_role(
                admin.user_id,
                schemas.RoleAssignmentRequest(role_name=RoleName.hr),
                actor,
            )
        )
