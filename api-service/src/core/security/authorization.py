from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.features.staff.models import DepartmentManager, Employee
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import RoleName
from src.core.db.database import get_db
from src.core.exceptions import ForbiddenException, NotFoundException


class AuthorizationPolicy:
    """Object-level employee scope shared by PII-bearing features."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_current_employee_id(self, current_user: User) -> uuid.UUID:
        employee_id = await self.db.scalar(
            select(Employee.employee_id).where(Employee.user_id == current_user.user_id)
        )
        if employee_id is None:
            raise NotFoundException("Employee profile")
        return employee_id

    async def get_viewable_employee_ids(
        self,
        current_user: User,
    ) -> set[uuid.UUID] | None:
        """Return None for unrestricted HR/admin, otherwise the exact allowed IDs."""
        if current_user.role_name in {RoleName.admin, RoleName.hr}:
            return None

        current_employee_id = await self.get_current_employee_id(current_user)
        if current_user.role_name == RoleName.employee:
            return {current_employee_id}
        if current_user.role_name != RoleName.manager:
            return set()

        managed_department_ids = select(DepartmentManager.department_id).where(
            DepartmentManager.manager_id == current_employee_id
        )
        result = await self.db.execute(
            select(Employee.employee_id).where(
                or_(
                    Employee.employee_id == current_employee_id,
                    Employee.manager_id == current_employee_id,
                    Employee.department_id.in_(managed_department_ids),
                )
            )
        )
        return set(result.scalars().all())

    async def ensure_can_view_employee(
        self,
        current_user: User,
        employee_id: uuid.UUID | None,
    ) -> None:
        allowed_ids = await self.get_viewable_employee_ids(current_user)
        if allowed_ids is None:
            return
        if employee_id is None or employee_id not in allowed_ids:
            raise ForbiddenException("You do not have access to this employee")

    async def scope_for_employee_query(
        self,
        current_user: User,
        requested_employee_id: uuid.UUID | None,
    ) -> set[uuid.UUID] | None:
        allowed_ids = await self.get_viewable_employee_ids(current_user)
        if (
            requested_employee_id is not None
            and allowed_ids is not None
            and requested_employee_id not in allowed_ids
        ):
            raise ForbiddenException("You do not have access to this employee")
        return allowed_ids

    async def ensure_manager_is_self(
        self,
        current_user: User,
        manager_employee_id: uuid.UUID,
    ) -> None:
        if current_user.role_name in {RoleName.admin, RoleName.hr}:
            return
        current_employee_id = await self.get_current_employee_id(current_user)
        if (
            current_user.role_name != RoleName.manager
            or current_employee_id != manager_employee_id
        ):
            raise ForbiddenException("Managers can only list their own subordinates")


def get_authorization_policy(
    db: AsyncSession = Depends(get_db),
) -> AuthorizationPolicy:
    return AuthorizationPolicy(db)
