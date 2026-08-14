from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.features.staff.models import Department, Employee, Position
from src.api.v1.features.users.models import Role, User
from src.api.v1.shared.enums import EmployeeStatus, RoleName, UserStatus
from src.core.configs.settings import settings
from src.core.db.database import AsyncSessionLocal
from src.core.security.authentication import hash_password
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)

DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "Admin12345"
SYSTEM_DEPARTMENT_NAME = "System"
SYSTEM_DEPARTMENT_CODE = "SYS"
SYSTEM_POSITION_NAME = "System Administrator"
SYSTEM_POSITION_CODE = "SYS_ADMIN"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
KNOWN_ENVIRONMENTS = {
    "dev": "development",
    "development": "development",
    "local": "development",
    "prod": "production",
    "production": "production",
    "stage": "staging",
    "staging": "staging",
    "test": "test",
    "testing": "test",
}


@dataclass(frozen=True)
class BootstrapIdentity:
    email: str
    password: str
    full_name: str


def _validated_environment() -> str:
    configured = settings.environment.strip().lower()
    try:
        return KNOWN_ENVIRONMENTS[configured]
    except KeyError as exc:
        raise ValueError(
            "bootstrap admin is not allowed for an unknown environment"
        ) from exc


def _validate_bootstrap_identity() -> BootstrapIdentity:
    _validated_environment()
    email = settings.bootstrap_admin_email.strip().lower()
    password = settings.bootstrap_admin_password
    full_name = settings.bootstrap_admin_full_name.strip()

    if not email:
        raise ValueError("bootstrap_admin_email must not be empty")
    if not EMAIL_PATTERN.match(email):
        raise ValueError("bootstrap_admin_email is not a valid email")
    if email == DEFAULT_ADMIN_EMAIL or password == DEFAULT_ADMIN_PASSWORD:
        raise ValueError("Known default bootstrap admin credentials are not allowed")
    if (
        len(password) < 12
        or not any(character.islower() for character in password)
        or not any(character.isupper() for character in password)
        or not any(character.isdigit() for character in password)
        or not any(not character.isalnum() for character in password)
    ):
        raise ValueError(
            "bootstrap_admin_password must be at least 12 characters and include "
            "uppercase, lowercase, numeric and special characters"
        )
    if not full_name:
        raise ValueError("bootstrap_admin_full_name must not be empty")

    return BootstrapIdentity(email=email, password=password, full_name=full_name)


async def get_or_create_admin_role(session: AsyncSession) -> Role:
    role = await session.scalar(select(Role).where(Role.name == RoleName.admin))
    if role is not None:
        return role

    role = Role(name=RoleName.admin, description="System administrator")
    session.add(role)
    await session.flush()
    logger.info("created role: admin")
    return role


async def get_or_create_system_department(session: AsyncSession) -> Department:
    department = await session.scalar(
        select(Department).where(Department.code == SYSTEM_DEPARTMENT_CODE)
    )
    if department is None:
        department = await session.scalar(
            select(Department).where(Department.name == SYSTEM_DEPARTMENT_NAME)
        )
    if department is not None:
        return department

    department = Department(
        name=SYSTEM_DEPARTMENT_NAME,
        code=SYSTEM_DEPARTMENT_CODE,
        description="Bootstrap system department",
        is_active=True,
    )
    session.add(department)
    await session.flush()
    logger.info("created department: %s", SYSTEM_DEPARTMENT_NAME)
    return department


async def get_or_create_system_position(session: AsyncSession) -> Position:
    position = await session.scalar(
        select(Position).where(Position.code == SYSTEM_POSITION_CODE)
    )
    if position is None:
        position = await session.scalar(
            select(Position).where(Position.name == SYSTEM_POSITION_NAME)
        )
    if position is not None:
        return position

    position = Position(
        name=SYSTEM_POSITION_NAME,
        code=SYSTEM_POSITION_CODE,
        description="Bootstrap system administrator position",
        is_active=True,
    )
    session.add(position)
    await session.flush()
    logger.info("created position: %s", SYSTEM_POSITION_NAME)
    return position


async def generate_admin_employee_code(session: AsyncSession) -> str:
    seq = 1
    while True:
        candidate = f"ADM{seq:06d}"
        existing = await session.scalar(
            select(Employee.employee_id).where(Employee.employee_code == candidate)
        )
        if existing is None:
            return candidate
        seq += 1


async def ensure_admin_user(
    session: AsyncSession,
    identity: BootstrapIdentity,
    role: Role,
) -> tuple[User, bool]:
    admin_user = await session.scalar(select(User).where(User.email == identity.email))
    if admin_user is None:
        admin_user = User(
            email=identity.email,
            password_hash=hash_password(identity.password),
            role_id=role.role_id,
            status=UserStatus.active,
        )
        session.add(admin_user)
        await session.flush()
        logger.info("created admin user: %s", identity.email)
        return admin_user, True

    if (
        admin_user.role_id != role.role_id
        or admin_user.status != UserStatus.active
    ):
        raise RuntimeError(
            "bootstrap email belongs to an existing non-admin or inactive account"
        )
    return admin_user, False


async def ensure_admin_staff(
    session: AsyncSession,
    admin_user: User,
    full_name: str,
    department: Department,
    position: Position,
    *,
    allow_create: bool,
) -> tuple[Employee, bool]:
    admin_staff = await session.scalar(
        select(Employee).where(Employee.user_id == admin_user.user_id)
    )
    if admin_staff is None:
        if not allow_create:
            raise RuntimeError(
                "bootstrap admin already exists without its expected employee record"
            )
        employee_code = await generate_admin_employee_code(session)
        admin_staff = Employee(
            user_id=admin_user.user_id,
            employee_code=employee_code,
            full_name=full_name,
            department_id=department.department_id,
            position_id=position.position_id,
            status=EmployeeStatus.active,
        )
        session.add(admin_staff)
        await session.flush()
        logger.info("created admin staff: %s", employee_code)
        return admin_staff, True

    if (
        admin_staff.status != EmployeeStatus.active
        or admin_staff.department_id != department.department_id
        or admin_staff.position_id != position.position_id
    ):
        raise RuntimeError(
            "bootstrap admin employee record exists with unexpected attributes"
        )
    return admin_staff, False


async def ensure_bootstrap_admin() -> None:
    if not settings.bootstrap_admin_enabled:
        logger.info("bootstrap disabled")
        return

    identity = _validate_bootstrap_identity()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            role = await get_or_create_admin_role(session)
            department = await get_or_create_system_department(session)
            position = await get_or_create_system_position(session)

            admin_user, user_created = await ensure_admin_user(session, identity, role)
            _admin_staff, staff_created = await ensure_admin_staff(
                session=session,
                admin_user=admin_user,
                full_name=identity.full_name,
                department=department,
                position=position,
                allow_create=user_created,
            )

            if not user_created and not staff_created:
                logger.info("bootstrap admin is already provisioned: %s", identity.email)
            elif user_created and staff_created:
                logger.info("bootstrap admin created: %s", identity.email)
            else:
                raise RuntimeError("bootstrap admin transaction is incomplete")
