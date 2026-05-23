from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.api.v1.shared.enums import RoleName, UserStatus

USERNAME_PATTERN = r"^[a-zA-Z0-9_.-]{4,50}$"
PASSWORD_MIN_LENGTH = 8


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: int
    name: RoleName
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class UserBase(BaseModel):
    username: str = Field(
        ...,
        min_length=4,
        max_length=50,
        pattern=USERNAME_PATTERN,
        description="Allowed chars: a-z, A-Z, 0-9, _, ., -",
    )
    status: UserStatus = UserStatus.active


class UserCreate(UserBase):
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)
    role_names: list[RoleName] = Field(default_factory=lambda: [RoleName.employee], min_length=1)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("Password must include at least one letter")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Password must include at least one digit")
        return value

    @field_validator("role_names")
    @classmethod
    def validate_unique_roles(cls, value: list[RoleName]) -> list[RoleName]:
        if len(set(value)) != len(value):
            raise ValueError("role_names contains duplicate values")
        return value


class UserUpdate(BaseModel):
    username: str | None = Field(
        default=None,
        min_length=4,
        max_length=50,
        pattern=USERNAME_PATTERN,
    )
    status: UserStatus | None = None
    password: str | None = Field(default=None, min_length=PASSWORD_MIN_LENGTH, max_length=128)
    role_names: list[RoleName] | None = Field(default=None, min_length=1)

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

    @field_validator("role_names")
    @classmethod
    def validate_unique_roles(cls, value: list[RoleName] | None) -> list[RoleName] | None:
        if value is None:
            return value
        if len(set(value)) != len(value):
            raise ValueError("role_names contains duplicate values")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    username: str
    status: UserStatus
    last_login_at: datetime | None = None
    role_names: list[RoleName] = Field(default_factory=list)
    roles: list[RoleRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UserRoleAssignRequest(BaseModel):
    role_names: list[RoleName] = Field(..., min_length=1)

    @field_validator("role_names")
    @classmethod
    def validate_unique_roles(cls, value: list[RoleName]) -> list[RoleName]:
        if len(set(value)) != len(value):
            raise ValueError("role_names contains duplicate values")
        return value


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
