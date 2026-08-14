from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.encoders import jsonable_encoder

from src.api.v1.features.audit import schemas
from src.api.v1.features.audit.repo import AuditRepo, get_audit_repo
from src.core.exceptions import (
    AppException,
    DatabaseException,
    NotFoundException,
    ValidationException,
)
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class AuditService:
    def __init__(self, audit_repo: AuditRepo):
        self.audit_repo = audit_repo

    async def create_audit_log(
        self,
        payload: schemas.AuditLogCreate,
    ) -> schemas.AuditLogRead:
        try:
            if not payload.object_type.strip():
                raise ValidationException(
                    "object_type must contain at least one non-whitespace character"
                )
            if payload.performed_by is not None and not await self.audit_repo.user_exists(
                payload.performed_by
            ):
                raise NotFoundException("Audit user")

            normalized_payload = payload.model_copy(
                update={
                    "old_value": jsonable_encoder(payload.old_value),
                    "new_value": jsonable_encoder(payload.new_value),
                }
            )
            audit_log = await self.audit_repo.create_audit_log(normalized_payload)
            logger.info(
                "Audit log created: log_id=%s action=%s object_type=%s object_id=%s",
                audit_log.log_id,
                audit_log.action,
                audit_log.object_type,
                audit_log.object_id,
            )
            return schemas.AuditLogRead.model_validate(audit_log)
        except AppException:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to create audit log: action=%s object_type=%s",
                payload.action,
                payload.object_type,
            )
            raise DatabaseException("Failed to create audit log") from exc

    async def get_audit_log(self, log_id: uuid.UUID) -> schemas.AuditLogRead:
        try:
            audit_log = await self.audit_repo.get_audit_log_by_id(log_id)
            if audit_log is None:
                raise NotFoundException("Audit log")
            return schemas.AuditLogRead.model_validate(audit_log)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Failed to get audit log: log_id=%s", log_id)
            raise DatabaseException("Failed to get audit log") from exc

    async def list_audit_logs(
        self,
        query: schemas.AuditLogListQuery,
    ) -> schemas.AuditLogListResponse:
        try:
            audit_logs, total = await self.audit_repo.list_audit_logs(query)
            return schemas.AuditLogListResponse(
                items=[schemas.AuditLogRead.model_validate(log) for log in audit_logs],
                total=total,
                page=query.page,
                page_size=query.page_size,
            )
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Failed to list audit logs")
            raise DatabaseException("Failed to list audit logs") from exc


def get_audit_service(
    audit_repo: AuditRepo = Depends(get_audit_repo),
) -> AuditService:
    return AuditService(audit_repo)
