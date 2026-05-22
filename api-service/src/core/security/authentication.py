import uuid
from datetime import datetime, timedelta, timezone
from typing import Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.entities.auths import Auth
from app.core.db.database import get_db
from app.core.db.enums import StaffRole
from app.core.configs.config import configs

JWT_SECRET_KEY = configs.JWT_SECRET_KEY
ALGORITHM = configs.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = configs.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = configs.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return bcrypt_context.hash(password)


def create_access_token(user_id: str, role: str):
    return create_token(
        data={
            "sub": str(user_id),
            "role": role,
            "type": "access"
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(user_id: str):
    return create_token(
        data={
            "sub": str(user_id),
            "type": "refresh"
        },
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )


def create_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str):
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])


async def get_current_user(
    token: str = Depends(oauth2_bearer),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    result = await db.execute(select(Auth).where(Auth.id == user_uuid))
    user = result.scalars().first()

    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_roles(*allowed_roles: StaffRole):
    async def role_checker(current_user: Auth = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden"
            )
        return current_user

    return role_checker
