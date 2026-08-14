from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.features.audit import schemas
from src.api.v1.features.audit.models import AuditLog
from src.api.v1.features.users.models import User
from src.core.db.database import get_db
from src.core.exceptions import DatabaseException
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class AuditRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def user_exists(self, user_id: uuid.UUID) -> bool:
        try:
            stmt = select(User.user_id).where(User.user_id == user_id)
            return (await self.db.execute(stmt)).first() is not None
        except Exception as exc:
            logger.exception("Failed to check audit user: user_id=%s", user_id)
            raise DatabaseException("Failed to check audit user") from exc

    async def create_audit_log(
        self,
        payload: schemas.AuditLogCreate,
    ) -> AuditLog:
        audit_log = AuditLog(
            performed_by=payload.performed_by,
            action=payload.action,
            object_type=payload.object_type.strip(),
            object_id=payload.object_id.strip() if payload.object_id else None,
            old_value=payload.old_value,
            new_value=payload.new_value,
            reason=payload.reason.strip() if payload.reason else None,
            ip_address=payload.ip_address.strip() if payload.ip_address else None,
            user_agent=payload.user_agent.strip() if payload.user_agent else None,
        )
        self.db.add(audit_log)

        try:
            await self.db.commit()
            await self.db.refresh(audit_log)
            return audit_log
        except Exception as exc:
            await self.db.rollback()
            logger.exception(
                "Failed to create audit log: action=%s object_type=%s object_id=%s",
                payload.action,
                payload.object_type,
                payload.object_id,
            )
            raise DatabaseException("Failed to create audit log") from exc

    async def get_audit_log_by_id(self, log_id: uuid.UUID) -> AuditLog | None:
        try:
            stmt = select(AuditLog).where(AuditLog.log_id == log_id)
            return await self.db.scalar(stmt)
        except Exception as exc:
            logger.exception("Failed to get audit log: log_id=%s", log_id)
            raise DatabaseException("Failed to get audit log") from exc

    async def list_audit_logs(
        self,
        query: schemas.AuditLogListQuery,
    ) -> tuple[list[AuditLog], int]:
        try:
            stmt: Select = select(AuditLog)

            if query.performed_by is not None:
                stmt = stmt.where(AuditLog.performed_by == query.performed_by)
            if query.action is not None:
                stmt = stmt.where(AuditLog.action == query.action)
            if query.object_type is not None:
                stmt = stmt.where(AuditLog.object_type == query.object_type.strip())
            if query.object_id is not None:
                stmt = stmt.where(AuditLog.object_id == query.object_id.strip())
            if query.created_from is not None:
                stmt = stmt.where(AuditLog.created_at >= query.created_from)
            if query.created_to is not None:
                stmt = stmt.where(AuditLog.created_at <= query.created_to)

            count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
            total = int((await self.db.scalar(count_stmt)) or 0)

            stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.log_id.desc())
            stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
            result = await self.db.execute(stmt)
            return list(result.scalars().all()), total
        except Exception as exc:
            logger.exception("Failed to list audit logs")
            raise DatabaseException("Failed to list audit logs") from exc


def get_audit_repo(db: AsyncSession = Depends(get_db)) -> AuditRepo:
    return AuditRepo(db)
