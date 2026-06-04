from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import Depends
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.features.staff.employees import schemas
from src.api.v1.features.staff.models import Department, Employee, Position
from src.api.v1.shared.enums import EmployeeStatus
from src.api.v1.features.users.models import User
from src.core.db.database import get_db
from src.utils.exeptions import ConflictException, DatabaseException, NotFoundException
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class EmployeeRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_optional(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    async def employee_code_exists(
        self,
        employee_code: str | None,
        exclude_employee_id: uuid.UUID | None = None,
    ) -> bool:
        normalized_code = self._normalize_optional(employee_code)
        if normalized_code is None:
            return False

        stmt = select(Employee.employee_id).where(Employee.employee_code == normalized_code)
        if exclude_employee_id is not None:
            stmt = stmt.where(Employee.employee_id != exclude_employee_id)
        return (await self.db.execute(stmt)).first() is not None

    async def user_exists(self, user_id: uuid.UUID | None) -> bool:
        if user_id is None:
            return False
        stmt = select(User.user_id).where(User.user_id == user_id)
        return (await self.db.execute(stmt)).first() is not None

    async def user_linked_to_other_employee(
        self,
        user_id: uuid.UUID | None,
        exclude_employee_id: uuid.UUID | None = None,
    ) -> bool:
        if user_id is None:
            return False
        stmt = select(Employee.employee_id).where(Employee.user_id == user_id)
        if exclude_employee_id is not None:
            stmt = stmt.where(Employee.employee_id != exclude_employee_id)
        return (await self.db.execute(stmt)).first() is not None

    async def department_exists(self, department_id: int | None) -> Department | None:
        if department_id is None:
            return None
        stmt = select(Department).where(Department.department_id == department_id)
        return await self.db.scalar(stmt)

    async def position_exists(self, position_id: int | None) -> Position | None:
        if position_id is None:
            return None
        stmt = select(Position).where(Position.position_id == position_id)
        return await self.db.scalar(stmt)

    async def manager_exists(self, manager_id: uuid.UUID | None) -> bool:
        if manager_id is None:
            return False
        stmt = select(Employee.employee_id).where(Employee.employee_id == manager_id)
        return (await self.db.execute(stmt)).first() is not None

    async def get_employee_by_id(self, employee_id: uuid.UUID) -> Employee | None:
        return await self.db.scalar(select(Employee).where(Employee.employee_id == employee_id))

    async def get_employee_or_404(self, employee_id: uuid.UUID) -> Employee:
        employee = await self.get_employee_by_id(employee_id)
        if employee is None:
            raise NotFoundException("Employee")
        return employee

    async def get_employee_by_code(self, employee_code: str) -> Employee | None:
        return await self.db.scalar(
            select(Employee).where(Employee.employee_code == employee_code.strip())
        )

    async def list_employees(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        department_id: int | None = None,
        position_id: int | None = None,
        manager_id: uuid.UUID | None = None,
        status=None,
    ) -> tuple[list[Employee], int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        offset = (page - 1) * page_size
        stmt: Select = select(Employee)

        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Employee.employee_code.ilike(term),
                    Employee.full_name.ilike(term),
                    Employee.phone.ilike(term),
                )
            )

        if department_id is not None:
            stmt = stmt.where(Employee.department_id == department_id)
        if position_id is not None:
            stmt = stmt.where(Employee.position_id == position_id)
        if manager_id is not None:
            stmt = stmt.where(Employee.manager_id == manager_id)
        if status is not None:
            stmt = stmt.where(Employee.status == status)

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int((await self.db.scalar(count_stmt)) or 0)

        result = await self.db.execute(
            stmt.order_by(Employee.created_at.desc()).offset(offset).limit(page_size)
        )
        employees = result.scalars().all()
        return list(employees), total

    async def create_employee(
        self,
        payload: schemas.EmployeeCreate,
        registered_by: uuid.UUID | None = None,
    ) -> Employee:
        employee_code = await self.generate_employee_code()

        if await self.employee_code_exists(employee_code):
            raise ConflictException("Employee code already exists")

        employee = Employee(
            user_id=payload.user_id,
            registered_by=registered_by,
            employee_code=employee_code,
            full_name=payload.full_name.strip(),
            phone=payload.phone,
            avatar_url=payload.avatar_url,
            department_id=payload.department_id,
            position_id=payload.position_id,
            manager_id=payload.manager_id,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            address=payload.address,
            hire_date=payload.hire_date,
            resignation_date=payload.resignation_date,
            status=payload.status,
        )
        self.db.add(employee)
        try:
            await self.db.commit()
            await self.db.refresh(employee)
            return employee
        except Exception as exc:
            await self.db.rollback()
            logger.exception(
                "Failed to create employee: employee_code=%s",
                employee_code,
            )
            raise DatabaseException("Failed to create employee") from exc

    async def generate_employee_code(self, year: int | None = None) -> str:
        target_year = year or datetime.now().year
        prefix = f"EMP_{target_year}_"
        result = await self.db.execute(
            select(Employee.employee_code).where(Employee.employee_code.like(f"{prefix}%"))
        )
        existing_codes = result.scalars().all()

        max_seq = 0
        for code in existing_codes:
            if not code or not code.startswith(prefix):
                continue
            suffix = code[len(prefix):]
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))

        next_seq = max_seq + 1
        return f"{prefix}{next_seq:04d}"

    async def update_employee(
        self,
        employee_id: uuid.UUID,
        payload: schemas.EmployeeUpdate,
    ) -> Employee:
        employee = await self.get_employee_or_404(employee_id)
        changed = False

        values = payload.model_dump(exclude_unset=True)

        if "employee_code" in values and values["employee_code"] is not None:
            normalized_code = values["employee_code"].strip()
            if normalized_code != employee.employee_code:
                if await self.employee_code_exists(
                    normalized_code,
                    exclude_employee_id=employee_id,
                ):
                    raise ConflictException("Employee code already exists")
                employee.employee_code = normalized_code
                changed = True

        if "full_name" in values and values["full_name"] is not None:
            normalized_name = values["full_name"].strip()
            if normalized_name != employee.full_name:
                employee.full_name = normalized_name
                changed = True

        for field in (
            "user_id",
            "phone",
            "avatar_url",
            "department_id",
            "position_id",
            "manager_id",
            "date_of_birth",
            "gender",
            "address",
            "hire_date",
            "resignation_date",
            "status",
        ):
            if field not in values:
                continue
            new_value = values[field]
            if getattr(employee, field) != new_value:
                setattr(employee, field, new_value)
                changed = True

        if changed:
            try:
                await self.db.commit()
            except Exception as exc:
                await self.db.rollback()
                logger.exception(
                    "Failed to update employee: employee_id=%s",
                    employee_id,
                )
                raise DatabaseException("Failed to update employee") from exc

        updated = await self.get_employee_by_id(employee_id)
        if updated is None:
            raise DatabaseException("Failed to reload updated employee")
        return updated

    async def delete_employee(self, employee_id: uuid.UUID) -> None:
        employee = await self.get_employee_or_404(employee_id)
        try:
            await self.db.delete(employee)
            await self.db.commit()
        except Exception as exc:
            await self.db.rollback()
            logger.exception(
                "Failed to delete employee: employee_id=%s",
                employee_id,
            )
            raise DatabaseException("Failed to delete employee") from exc

    async def deactivate_employee(self, employee_id: uuid.UUID) -> Employee:
        employee = await self.get_employee_or_404(employee_id)
        if employee.status == EmployeeStatus.inactive:
            return employee

        employee.status = EmployeeStatus.inactive
        try:
            await self.db.commit()
            await self.db.refresh(employee)
            return employee
        except Exception as exc:
            await self.db.rollback()
            logger.exception(
                "Failed to deactivate employee: employee_id=%s",
                employee_id,
            )
            raise DatabaseException("Failed to deactivate employee") from exc


def get_employee_repo(db: AsyncSession = Depends(get_db)) -> EmployeeRepo:
    return EmployeeRepo(db)
