from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status

from src.api.v1.features.staff.employees import schemas
from src.api.v1.features.staff.employees.service import (
    EmployeeService,
    get_employee_service,
)
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import RoleName
from src.api.v1.features.staff.models import Employee
from src.core.dependencies.auth import (
    get_current_employee,
    get_current_user,
    require_roles,
)
from src.core.security.authorization import (
    AuthorizationPolicy,
    get_authorization_policy,
)

router = APIRouter(prefix="/employees", tags=["Staff-Employees"])


@router.get("/me", response_model=schemas.EmployeeRead)
async def get_my_employee_profile(
    current_employee: Employee = Depends(get_current_employee),
) -> schemas.EmployeeRead:
    return current_employee


@router.patch("/me", response_model=schemas.EmployeeRead)
async def update_my_employee_profile(
    payload: schemas.EmployeeSelfUpdate,
    current_employee: Employee = Depends(get_current_employee),
    service: EmployeeService = Depends(get_employee_service),
) -> schemas.EmployeeRead:
    safe_payload = schemas.EmployeeUpdate(
        **payload.model_dump(exclude_unset=True),
    )
    return await service.update_employee(
        employee_id=current_employee.employee_id,
        payload=safe_payload,
    )


@router.get("/code/{employee_code}", response_model=schemas.EmployeeRead)
async def get_employee_by_code(
    employee_code: str,
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(
        require_roles(RoleName.admin, RoleName.hr, RoleName.manager)
    ),
    policy: AuthorizationPolicy = Depends(get_authorization_policy),
) -> schemas.EmployeeRead:
    employee = await service.get_employee_by_code(employee_code)
    await policy.ensure_can_view_employee(current_user, employee.employee_id)
    return employee


@router.get(
    "/{employee_id}/subordinates",
    response_model=list[schemas.EmployeeSummary],
)
async def list_subordinates(
    employee_id: uuid.UUID,
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(
        require_roles(RoleName.manager, RoleName.hr, RoleName.admin)
    ),
    policy: AuthorizationPolicy = Depends(get_authorization_policy),
) -> list[schemas.EmployeeSummary]:
    await policy.ensure_manager_is_self(current_user, employee_id)
    return await service.list_subordinates(employee_id)


@router.get("/{employee_id}", response_model=schemas.EmployeeRead)
async def get_employee(
    employee_id: uuid.UUID,
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(get_current_user),
    policy: AuthorizationPolicy = Depends(get_authorization_policy),
) -> schemas.EmployeeRead:
    await policy.ensure_can_view_employee(current_user, employee_id)
    return await service.get_employee(employee_id)


@router.get("/", response_model=dict)
async def list_employees(
    query: schemas.EmployeeListQuery = Depends(),
    service: EmployeeService = Depends(get_employee_service),
    current_user: User = Depends(
        require_roles(RoleName.admin, RoleName.hr, RoleName.manager)
    ),
    policy: AuthorizationPolicy = Depends(get_authorization_policy),
) -> dict:
    visible_employee_ids = await policy.scope_for_employee_query(current_user, None)
    return await service.list_employees(
        query,
        visible_employee_ids=visible_employee_ids,
    )


@router.patch("/{employee_id}", response_model=schemas.EmployeeRead)
async def update_employee(
    employee_id: uuid.UUID,
    payload: schemas.EmployeeUpdate,
    service: EmployeeService = Depends(get_employee_service),
    _: User = Depends(require_roles(RoleName.admin, RoleName.hr)),
) -> schemas.EmployeeRead:
    return await service.update_employee(employee_id, payload)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: uuid.UUID,
    service: EmployeeService = Depends(get_employee_service),
    _: User = Depends(require_roles(RoleName.admin)),
) -> Response:
    await service.delete_employee(employee_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/activate/{employee_id}", response_model=schemas.EmployeeRead)
async def activate_employee(
    employee_id: uuid.UUID,
    service: EmployeeService = Depends(get_employee_service),
    _: User = Depends(require_roles(RoleName.admin, RoleName.hr)),
) -> schemas.EmployeeRead:
    return await service.activate_employee(employee_id)
