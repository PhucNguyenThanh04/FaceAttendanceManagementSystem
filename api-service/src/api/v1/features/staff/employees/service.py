from __future__ import annotations

import uuid

from fastapi import Depends

from src.api.v1.features.staff.employees import schemas
from src.api.v1.features.staff.employees.employee_repo import EmployeeRepo, get_employee_repo
from src.api.v1.shared.enums import EmployeeStatus
from src.utils.exeptions import BadRequestException, ConflictException, NotFoundException
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class EmployeeService:
    def __init__(self, employee_repo: EmployeeRepo):
        self.employee_repo = employee_repo

    @staticmethod
    def _to_read(employee) -> schemas.EmployeeRead:
        return schemas.EmployeeRead.model_validate(employee)

    async def employee_code_exists(self, employee_code: str) -> bool:
        return await self.employee_repo.employee_code_exists(employee_code)

    async def department_exists_active(self, department_id: int) -> None:
        dep = await self.employee_repo.department_exists(department_id)
        if dep is None:
            raise BadRequestException("Department not found")
        if not dep.is_active:
            raise BadRequestException("Department is inactive")

    async def position_exists_active(self, position_id: int) -> None:
        pos = await self.employee_repo.position_exists(position_id)
        if pos is None:
            raise BadRequestException("Position not found")
        if not pos.is_active:
            raise BadRequestException("Position is inactive")


    async def _validate_references_on_create(self, payload: schemas.EmployeeCreate) -> None:
        if payload.user_id is not None:
            if not await self.employee_repo.user_exists(payload.user_id):
                raise BadRequestException("User not found")
            if await self.employee_repo.user_linked_to_other_employee(payload.user_id):
                raise ConflictException("User is already linked to another employee")
        if payload.employee_code is not None and await self.employee_repo.employee_code_exists(
            payload.employee_code
        ):
            raise ConflictException("Employee code already exists")

        if payload.department_id is not None and not await self.employee_repo.department_exists(
            payload.department_id
        ):
            raise BadRequestException("Department not found")

        if payload.position_id is not None and not await self.employee_repo.position_exists(
            payload.position_id
        ):
            raise BadRequestException("Position not found")

        if payload.manager_id is not None and not await self.employee_repo.manager_exists(
            payload.manager_id
        ):
            raise BadRequestException("Manager not found")

    async def _validate_references_on_update(
        self,
        employee_id: uuid.UUID,
        payload: schemas.EmployeeUpdate,
    ) -> None:
        if payload.user_id is not None:
            if not await self.employee_repo.user_exists(payload.user_id):
                raise BadRequestException("User not found")
            if await self.employee_repo.user_linked_to_other_employee(
                payload.user_id,
                exclude_employee_id=employee_id,
            ):
                raise ConflictException("User is already linked to another employee")

        if payload.department_id is not None and not await self.employee_repo.department_exists(
            payload.department_id
        ):
            raise BadRequestException("Department not found")

        if payload.position_id is not None and not await self.employee_repo.position_exists(
            payload.position_id
        ):
            raise BadRequestException("Position not found")

        if payload.manager_id is not None:
            if payload.manager_id == employee_id:
                raise BadRequestException("Employee cannot be their own manager")
            if not await self.employee_repo.manager_exists(payload.manager_id):
                raise BadRequestException("Manager not found")

    async def create_employee(
        self,
        payload: schemas.EmployeeCreate,
        registered_by: uuid.UUID | None = None,
    ) -> schemas.EmployeeRead:
        logger.info(
            "Create employee request: employee_code=%s user_id=%s full_name=%s registered_by=%s",
            payload.employee_code,
            payload.user_id,
            payload.full_name,
            registered_by,
        )

        if payload.employee_code:
            logger.info(
                "Create employee payload contains employee_code=%s but system will auto-generate",
                payload.employee_code,
            )

        await self._validate_references_on_create(payload)
        employee = await self.employee_repo.create_employee(
            payload=payload,
            registered_by=registered_by,
        )
        logger.info(
            "Employee created: employee_id=%s user_id=%s",
            employee.employee_id,
            employee.user_id,
        )
        return self._to_read(employee)

    async def get_employee(self, employee_id: uuid.UUID) -> schemas.EmployeeRead:
        employee = await self.employee_repo.get_employee_by_id(employee_id)
        if employee is None:
            logger.warning("Employee not found by id: employee_id=%s", employee_id)
            raise NotFoundException("Employee")
        return self._to_read(employee)

    async def get_employee_by_code(self, employee_code: str) -> schemas.EmployeeRead:
        employee = await self.employee_repo.get_employee_by_code(employee_code)
        if employee is None:
            logger.warning("Employee not found by code: employee_code=%s", employee_code)
            raise NotFoundException("Employee")
        return self._to_read(employee)

    async def list_employees(self, query: schemas.EmployeeListQuery) -> dict:
        employees, total = await self.employee_repo.list_employees(
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            department_id=query.department_id,
            position_id=query.position_id,
            manager_id=query.manager_id,
            status=query.status,
        )
        logger.info(
            "List employees: page=%s page_size=%s total=%s search=%s",
            query.page,
            query.page_size,
            total,
            query.search,
        )
        return {
            "items": [self._to_read(employee) for employee in employees],
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
        }

    async def update_employee(
        self,
        employee_id: uuid.UUID,
        payload: schemas.EmployeeUpdate,
    ) -> schemas.EmployeeRead:
        existing = await self.employee_repo.get_employee_by_id(employee_id)
        if existing is None:
            logger.warning("Update employee not found: employee_id=%s", employee_id)
            raise NotFoundException("Employee")

        if (
            payload.employee_code is not None
            and await self.employee_repo.employee_code_exists(
                payload.employee_code,
                exclude_employee_id=employee_id,
            )
        ):
            logger.warning(
                "Update employee conflict code: employee_id=%s employee_code=%s",
                employee_id,
                payload.employee_code,
            )
            raise ConflictException("Employee code already exists")

        await self._validate_references_on_update(employee_id, payload)

        updated = await self.employee_repo.update_employee(employee_id, payload)
        logger.info("Employee updated: employee_id=%s", employee_id)
        return self._to_read(updated)

    async def delete_employee(self, employee_id: uuid.UUID) -> None:
        employee = await self.employee_repo.get_employee_by_id(employee_id)
        if employee is None:
            logger.warning("Delete employee not found: employee_id=%s", employee_id)
            raise NotFoundException("Employee")
        await self.employee_repo.delete_employee(employee_id)
        logger.info("Employee deleted: employee_id=%s", employee_id)

    async def deactivate_employee(self, employee_id: uuid.UUID) -> schemas.EmployeeRead:
        employee = await self.employee_repo.get_employee_by_id(employee_id)
        if employee is None:
            logger.warning("Deactivate employee not found: employee_id=%s", employee_id)
            raise NotFoundException("Employee")

        if employee.status == EmployeeStatus.inactive:
            logger.info("Employee already inactive: employee_id=%s", employee_id)
            return self._to_read(employee)

        deactivated = await self.employee_repo.deactivate_employee(employee_id)
        logger.info("Employee deactivated: employee_id=%s", employee_id)
        return self._to_read(deactivated)


def get_employee_service(
    employee_repo: EmployeeRepo = Depends(get_employee_repo),
) -> EmployeeService:
    return EmployeeService(employee_repo=employee_repo)
