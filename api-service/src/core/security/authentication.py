import uuid
from datetime import datetime, timedelta, timezone
from typing import Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.configs.settings import settings

JWT_SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

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

