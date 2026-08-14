from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from src.api.v1.features.audit import schemas
from src.api.v1.features.audit.service import AuditService, get_audit_service
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import RoleName
from src.core.dependencies.auth import require_roles, verify_internal_api_key

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.post(
    "",
    response_model=schemas.AuditLogRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_api_key)],
)
async def create_audit_log(
    payload: schemas.AuditLogCreate,
    service: AuditService = Depends(get_audit_service),
) -> schemas.AuditLogRead:
    return await service.create_audit_log(payload)


@router.get("", response_model=schemas.AuditLogListResponse)
async def list_audit_logs(
    query: schemas.AuditLogListQuery = Depends(),
    service: AuditService = Depends(get_audit_service),
    _: User = Depends(require_roles(RoleName.admin)),
) -> schemas.AuditLogListResponse:
    return await service.list_audit_logs(query)


@router.get("/{log_id}", response_model=schemas.AuditLogRead)
async def get_audit_log(
    log_id: uuid.UUID,
    service: AuditService = Depends(get_audit_service),
    _: User = Depends(require_roles(RoleName.admin)),
) -> schemas.AuditLogRead:
    return await service.get_audit_log(log_id)
