"""
app/features/users/models.py

Bảng sở hữu:
  - users          : tài khoản đăng nhập
  - roles          : danh sách vai trò
  - user_roles     : junction M2M user ↔ role

Được import bởi: hầu hết mọi feature (FK đến users.user_id)
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.base import Base, TimestampMixin
from src.api.v1.shared.enums import RoleName, UserStatus

if TYPE_CHECKING:
    # Import vòng chỉ cho type hint, tránh circular import lúc runtime
    from src.api.v1.features.staff.models import Employee
    from src.api.v1.features.notifications.models import Notification
    from src.api.v1.features.audit.models import AuditLog
    from src.api.v1.features.system.models import SystemSetting


# ── users ──────────────────────────────────────────────────────────────────

class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.active,
        index=True,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    # user_roles (M2M sang roles, qua UserRole)
    user_roles: Mapped[List["UserRole"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",           # load cùng user — cần roles thường xuyên
    )

    # Convenience: truy cập trực tiếp danh sách Role object
    roles: Mapped[List["Role"]] = relationship(
        secondary="user_roles",
        viewonly=True,             # chỉ đọc, thao tác qua user_roles
        lazy="selectin",
    )

    # Quan hệ 1-1 sang Employee (một user có thể là một nhân viên)
    employee: Mapped[Optional["Employee"]] = relationship(
        back_populates="user",
        uselist=False,
        lazy="select",
    )

    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="user",
        lazy="select",
    )

    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="performed_by_user",
        foreign_keys="AuditLog.performed_by",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.user_id} username={self.username}>"

    @property
    def role_names(self) -> List[RoleName]:
        """Shortcut lấy danh sách tên role."""
        return [r.name for r in self.roles]

    def has_role(self, role: RoleName) -> bool:
        return role in self.role_names


# ── roles ──────────────────────────────────────────────────────────────────

class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    role_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[RoleName] = mapped_column(
        Enum(RoleName, name="role_name"),
        unique=True,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    user_roles: Mapped[List["UserRole"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


# ── user_roles (junction M2M) ──────────────────────────────────────────────

class UserRole(Base):
    """
    Bảng junction M2M users ↔ roles.
    Không dùng TimestampMixin vì chỉ có assigned_at, không có updated_at.
    """
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="user_roles")
    role: Mapped["Role"] = relationship(back_populates="user_roles")

    def __repr__(self) -> str:
        return f"<UserRole user={self.user_id} role={self.role_id}>"