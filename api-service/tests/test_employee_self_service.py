from __future__ import annotations

import asyncio
import uuid
from datetime import date, timedelta
from types import SimpleNamespace
from typing import cast

import pytest
from pydantic import ValidationError

from src.api.v1.features.staff.employees import controller, schemas
from src.api.v1.features.staff.employees.service import EmployeeService
from src.api.v1.features.staff.models import Employee


class FakeEmployeeService:
    def __init__(self) -> None:
        self.employee_id: uuid.UUID | None = None
        self.payload: schemas.EmployeeUpdate | None = None

    async def update_employee(
        self,
        employee_id: uuid.UUID,
        payload: schemas.EmployeeUpdate,
    ):
        self.employee_id = employee_id
        self.payload = payload
        return SimpleNamespace(employee_id=employee_id)


def test_self_update_only_forwards_personal_fields() -> None:
    employee_id = uuid.uuid4()
    service = FakeEmployeeService()
    payload = schemas.EmployeeSelfUpdate(
        phone="0912345678",
        address="Da Nang",
        gender="FEMALE",
    )

    asyncio.run(
        controller.update_my_employee_profile(
            payload=payload,
            current_employee=cast(Employee, SimpleNamespace(employee_id=employee_id)),
            service=cast(EmployeeService, service),
        )
    )

    assert service.employee_id == employee_id
    assert service.payload is not None
    assert service.payload.model_dump(exclude_unset=True) == {
        "phone": "0912345678",
        "address": "Da Nang",
        "gender": "female",
    }


@pytest.mark.parametrize(
    "forbidden_field",
    ["employee_code", "department_id", "position_id", "status", "manager_id"],
)
def test_self_update_rejects_managed_fields(forbidden_field: str) -> None:
    with pytest.raises(ValidationError):
        schemas.EmployeeSelfUpdate.model_validate({forbidden_field: "unsafe"})


@pytest.mark.parametrize(
    "payload",
    [
        {"avatar_url": "https://untrusted.example/avatar.png"},
        {"date_of_birth": date.today() + timedelta(days=1)},
    ],
)
def test_self_update_rejects_unsafe_personal_values(payload: dict) -> None:
    with pytest.raises(ValidationError):
        schemas.EmployeeSelfUpdate.model_validate(payload)
