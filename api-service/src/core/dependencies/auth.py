"""
FastAPI dependencies dùng chung: xác thực JWT, phân quyền role.
"""

from typing import Annotated
from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.configs.settings import settings
from src.core.db.database import get_db
from src.core.security.authentication import build_access_token_blacklist_key
from src.api.v1.features.users.models import User
from src.api.v1.features.staff.models import Employee
from src.api.v1.shared.enums import RoleName, UserStatus
from src.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException

bearer_scheme = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Security(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Decode JWT → load User từ DB. Dùng cho mọi endpoint cần auth."""
    credentials_exception = UnauthorizedException("Token không hợp lệ hoặc đã hết hạn")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        token_version_claim = payload.get("token_version")
        jti_claim = payload.get("jti")
        if user_id is None:
            raise credentials_exception
        if token_version_claim is None:
            raise credentials_exception
        if jti_claim is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is not None:
        is_blacklisted = await redis_client.get(build_access_token_blacklist_key(str(jti_claim)))
        if is_blacklisted:
            raise credentials_exception

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if int(token_version_claim) != int(user.token_version):
        raise credentials_exception
    if user.status != UserStatus.active:
        raise ForbiddenException("Tài khoản đã bị khóa hoặc vô hiệu hóa")
    return user


async def get_current_employee(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Employee:
    """Load Employee tương ứng với user đang đăng nhập."""
    result = await db.execute(
        select(Employee).where(Employee.user_id == current_user.user_id)
    )
    employee = result.scalar_one_or_none()
    if employee is None:
        raise NotFoundException("Employee profile")
    return employee


def require_roles(*roles: RoleName):
    """
    Factory tạo dependency kiểm tra role.

    Dùng:
        @router.get("/...", dependencies=[Depends(require_roles(RoleName.hr))])
    Hoặc:
        current_user: User = Depends(require_roles(RoleName.hr, RoleName.admin))
    """
    async def _check(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        user_role = current_user.role.name
        if user_role not in roles:
            raise ForbiddenException(f"Yêu cầu quyền: {', '.join(r.value for r in roles)}")
        return current_user
    return _check


# Shortcut dependencies hay dùng
RequireHR = Depends(require_roles(RoleName.hr, RoleName.admin))
RequireManager = Depends(require_roles(RoleName.manager, RoleName.hr, RoleName.admin))
RequireEmployee = Depends(get_current_user)  # mọi user đã login đều được
