from __future__ import annotations

import asyncio
import inspect
import uuid
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.features.attendance import controller as attendance_controller
from src.api.v1.features.shifts import controller as shifts_controller
from src.api.v1.features.staff.employees import controller as employees_controller
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import RoleName
from src.core.dependencies import auth
from src.core.exceptions import ForbiddenException
from src.core.security.authorization import AuthorizationPolicy


class FakeScalarResult:
    def __init__(self, values: set[uuid.UUID]) -> None:
        self.values = values

    def scalars(self) -> FakeScalarResult:
        return self

    def all(self) -> list[uuid.UUID]:
        return list(self.values)


class FakeDB:
    def __init__(
        self,
        current_employee_id: uuid.UUID,
        *,
        manager_scope: set[uuid.UUID] | None = None,
    ) -> None:
        self.current_employee_id = current_employee_id
        self.manager_scope = manager_scope or set()
        self.execute_calls = 0

    async def scalar(self, _statement):
        return self.current_employee_id

    async def execute(self, _statement):
        self.execute_calls += 1
        return FakeScalarResult(self.manager_scope)


def make_user(role_name: RoleName) -> User:
    return cast(
        User,
        SimpleNamespace(
            user_id=uuid.uuid4(),
            role_name=role_name,
        ),
    )


def make_policy(
    current_employee_id: uuid.UUID,
    *,
    manager_scope: set[uuid.UUID] | None = None,
) -> tuple[AuthorizationPolicy, FakeDB]:
    db = FakeDB(current_employee_id, manager_scope=manager_scope)
    return AuthorizationPolicy(cast(AsyncSession, db)), db


def test_employee_can_only_view_own_employee_object() -> None:
    own_employee_id = uuid.uuid4()
    another_employee_id = uuid.uuid4()
    policy, _ = make_policy(own_employee_id)
    employee = make_user(RoleName.employee)

    asyncio.run(policy.ensure_can_view_employee(employee, own_employee_id))
    with pytest.raises(ForbiddenException):
        asyncio.run(policy.ensure_can_view_employee(employee, another_employee_id))


def test_manager_can_view_only_self_direct_reports_and_managed_departments() -> None:
    manager_id = uuid.uuid4()
    direct_report_id = uuid.uuid4()
    managed_department_employee_id = uuid.uuid4()
    outside_scope_id = uuid.uuid4()
    allowed = {manager_id, direct_report_id, managed_department_employee_id}
    policy, db = make_policy(manager_id, manager_scope=allowed)
    manager = make_user(RoleName.manager)

    asyncio.run(policy.ensure_can_view_employee(manager, direct_report_id))
    asyncio.run(
        policy.ensure_can_view_employee(manager, managed_department_employee_id)
    )
    with pytest.raises(ForbiddenException):
        asyncio.run(policy.ensure_can_view_employee(manager, outside_scope_id))
    assert db.execute_calls == 3


@pytest.mark.parametrize("role_name", [RoleName.hr, RoleName.admin])
def test_hr_and_admin_have_unrestricted_employee_scope(role_name: RoleName) -> None:
    policy, db = make_policy(uuid.uuid4())

    asyncio.run(policy.ensure_can_view_employee(make_user(role_name), uuid.uuid4()))

    assert db.execute_calls == 0


def test_out_of_scope_query_filter_is_rejected_instead_of_ignored() -> None:
    own_employee_id = uuid.uuid4()
    policy, _ = make_policy(own_employee_id)

    with pytest.raises(ForbiddenException):
        asyncio.run(
            policy.scope_for_employee_query(
                make_user(RoleName.employee),
                uuid.uuid4(),
            )
        )


def test_manager_cannot_impersonate_another_manager_in_subordinate_route() -> None:
    manager_id = uuid.uuid4()
    policy, _ = make_policy(manager_id)

    with pytest.raises(ForbiddenException):
        asyncio.run(
            policy.ensure_manager_is_self(
                make_user(RoleName.manager),
                uuid.uuid4(),
            )
        )


def test_rag_api_key_is_not_a_generic_pii_superuser() -> None:
    assert not hasattr(auth, "get_current_user_or_rag_api_key")

    pii_controllers = (
        attendance_controller,
        employees_controller,
        shifts_controller,
    )
    for controller in pii_controllers:
        assert "get_current_user_or_rag_api_key" not in inspect.getsource(controller)
