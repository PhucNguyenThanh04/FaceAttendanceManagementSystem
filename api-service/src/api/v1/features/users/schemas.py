from __future__ import annotations

import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from src.api.v1.shared.enums import RoleName, UserStatus
from src.core.configs.settings import settings

EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
PASSWORD_MIN_LENGTH = 8
APP_TZ = ZoneInfo(settings.database_timezone)


def to_app_timezone(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(APP_TZ)


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: int
    name: RoleName
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_role_datetimes(self, value: datetime) -> str:
        return to_app_timezone(value).isoformat()


class UserBase(BaseModel):
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        pattern=EMAIL_PATTERN,
    )
    status: UserStatus = UserStatus.active


class UserCreate(UserBase):
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)
    role_name: RoleName = RoleName.employee

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("Password must include at least one letter")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Password must include at least one digit")
        return value


class UserUpdate(BaseModel):
    email: str | None = Field(
        default=None,
        min_length=5,
        max_length=255,
        pattern=EMAIL_PATTERN,
    )
    status: UserStatus | None = None
    password: str | None = Field(default=None, min_length=PASSWORD_MIN_LENGTH, max_length=128)
    role_name: RoleName | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not any(ch.isalpha() for ch in value):
            raise ValueError("Password must include at least one letter")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Password must include at least one digit")
        return value

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    status: UserStatus
    last_login_at: datetime | None = None
    role_name: RoleName
    role: RoleRead
    created_at: datetime
    updated_at: datetime

    @field_serializer("last_login_at", when_used="json")
    def serialize_last_login_at(self, value: datetime | None) -> str | None:
        converted = to_app_timezone(value)
        return converted.isoformat() if converted else None

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_user_datetimes(self, value: datetime) -> str:
        return to_app_timezone(value).isoformat()


class UserRoleAssignRequest(BaseModel):
    role_name: RoleName


class UserListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    search: str | None = Field(default=None, min_length=1, max_length=100)
    status: UserStatus | None = None
    role: RoleName | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("Password must include at least one letter")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Password must include at least one digit")
        return value

    @model_validator(mode="after")
    def validate_password_not_same(self) -> "ChangePasswordRequest":
        if self.old_password == self.new_password:
            raise ValueError("New password must be different from old password")
        return self
