"""
FastAPI dependencies dùng chung: xác thực JWT, phân quyền role.
"""

from typing import Annotated
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.configs.settings import settings
from src.core.db.database import get_db
from src.api.v1.features.users.models import User
from src.api.v1.features.staff.models import Employee
from src.api.v1.shared.enums import RoleName, UserStatus

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    db : AsyncSession = Depends(get_db)
) -> User:
    """Decode JWT → load User từ DB. Dùng cho mọi endpoint cần auth."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa hoặc vô hiệu hóa",
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hồ sơ nhân viên",
        )
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
        user_roles = {r.name for r in current_user.roles}
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Yêu cầu quyền: {', '.join(r.value for r in roles)}",
            )
        return current_user
    return _check


# Shortcut dependencies hay dùng
RequireHR = Depends(require_roles(RoleName.hr, RoleName.admin))
RequireManager = Depends(require_roles(RoleName.manager, RoleName.hr, RoleName.admin))
RequireEmployee = Depends(get_current_user)  # mọi user đã login đều được