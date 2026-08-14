from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from src.api.v1.shared.enums import EmployeeStatus, UserStatus
from src.core.bootstrap import admin_seed


class ScalarSession:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.added: list[Any] = []

    async def scalar(self, _statement: Any) -> Any:
        return self.result

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        return None


def configure_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    environment: str = "development",
    email: str = "bootstrap-admin@example.org",
    password: str = "Long-Random-Password-42",
) -> None:
    monkeypatch.setattr(admin_seed.settings, "environment", environment)
    monkeypatch.setattr(admin_seed.settings, "bootstrap_admin_email", email)
    monkeypatch.setattr(admin_seed.settings, "bootstrap_admin_password", password)
    monkeypatch.setattr(
        admin_seed.settings,
        "bootstrap_admin_full_name",
        "Bootstrap Administrator",
    )


def test_bootstrap_is_disabled_by_default() -> None:
    field = type(admin_seed.settings).model_fields["bootstrap_admin_enabled"]
    assert field.default is False


@pytest.mark.asyncio
async def test_disabled_bootstrap_does_not_open_a_database_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnexpectedSession:
        def __call__(self) -> None:
            raise AssertionError("disabled bootstrap must not access the database")

    monkeypatch.setattr(admin_seed.settings, "bootstrap_admin_enabled", False)
    monkeypatch.setattr(admin_seed, "AsyncSessionLocal", UnexpectedSession())

    await admin_seed.ensure_bootstrap_admin()


@pytest.mark.parametrize("environment", ["development", "test", "production"])
@pytest.mark.parametrize(
    ("email", "password"),
    [
        (admin_seed.DEFAULT_ADMIN_EMAIL, "Different-Strong-Password-42"),
        ("different@example.org", admin_seed.DEFAULT_ADMIN_PASSWORD),
    ],
)
def test_known_default_credentials_are_rejected_in_every_environment(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    email: str,
    password: str,
) -> None:
    configure_identity(
        monkeypatch,
        environment=environment,
        email=email,
        password=password,
    )

    with pytest.raises(ValueError, match="Known default"):
        admin_seed._validate_bootstrap_identity()


def test_unknown_environment_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_identity(monkeypatch, environment="customer-production-ish")

    with pytest.raises(ValueError, match="unknown environment"):
        admin_seed._validate_bootstrap_identity()


def test_production_with_weak_password_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_identity(
        monkeypatch,
        environment="production",
        password="alllowercasepassword",
    )

    with pytest.raises(ValueError, match="uppercase, lowercase"):
        admin_seed._validate_bootstrap_identity()


def test_enabled_bootstrap_with_missing_credentials_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_identity(monkeypatch, email="", password="")

    with pytest.raises(ValueError, match="email must not be empty"):
        admin_seed._validate_bootstrap_identity()


@pytest.mark.asyncio
async def test_absent_admin_user_is_created_without_client_supplied_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = ScalarSession(None)
    identity = admin_seed.BootstrapIdentity(
        email="new-admin@example.org",
        password="New-Strong-Password-42",
        full_name="New Administrator",
    )
    monkeypatch.setattr(admin_seed, "hash_password", lambda _: "derived-password-hash")

    admin_user, created = await admin_seed.ensure_admin_user(
        cast(Any, session),
        identity,
        cast(Any, SimpleNamespace(role_id=99)),
    )

    assert created is True
    assert admin_user.email == identity.email
    assert admin_user.password_hash == "derived-password-hash"
    assert admin_user.role_id == 99
    assert admin_user.status == UserStatus.active
    assert session.added == [admin_user]


@pytest.mark.asyncio
async def test_existing_user_is_never_promoted_or_reactivated() -> None:
    existing_user = SimpleNamespace(
        role_id="employee-role",
        status=UserStatus.inactive,
        password_hash="original-password-hash",
    )
    session = ScalarSession(existing_user)
    role = SimpleNamespace(role_id="admin-role")
    identity = admin_seed.BootstrapIdentity(
        email="existing@example.org",
        password="Long-Random-Password-42",
        full_name="Existing User",
    )

    with pytest.raises(RuntimeError, match="existing non-admin or inactive"):
        await admin_seed.ensure_admin_user(
            cast(Any, session),
            identity,
            cast(Any, role),
        )

    assert existing_user.role_id == "employee-role"
    assert existing_user.status == UserStatus.inactive
    assert existing_user.password_hash == "original-password-hash"
    assert session.added == []


@pytest.mark.asyncio
async def test_existing_active_admin_is_left_completely_unchanged() -> None:
    existing_user = SimpleNamespace(
        role_id="admin-role",
        status=UserStatus.active,
        password_hash="original-password-hash",
    )
    session = ScalarSession(existing_user)
    identity = admin_seed.BootstrapIdentity(
        email="existing-admin@example.org",
        password="New-Strong-Password-42",
        full_name="Existing Administrator",
    )

    returned_user, created = await admin_seed.ensure_admin_user(
        cast(Any, session),
        identity,
        cast(Any, SimpleNamespace(role_id="admin-role")),
    )

    assert returned_user is existing_user
    assert created is False
    assert existing_user.role_id == "admin-role"
    assert existing_user.status == UserStatus.active
    assert existing_user.password_hash == "original-password-hash"
    assert session.added == []


@pytest.mark.asyncio
async def test_existing_employee_is_never_reactivated_or_reassigned() -> None:
    existing_employee = SimpleNamespace(
        status=EmployeeStatus.inactive,
        department_id="sales",
        position_id="sales-representative",
    )
    session = ScalarSession(existing_employee)

    with pytest.raises(RuntimeError, match="unexpected attributes"):
        await admin_seed.ensure_admin_staff(
            cast(Any, session),
            cast(Any, SimpleNamespace(user_id="existing-user")),
            "Existing User",
            cast(Any, SimpleNamespace(department_id="system")),
            cast(Any, SimpleNamespace(position_id="system-admin")),
            allow_create=False,
        )

    assert existing_employee.status == EmployeeStatus.inactive
    assert existing_employee.department_id == "sales"
    assert existing_employee.position_id == "sales-representative"
    assert session.added == []
