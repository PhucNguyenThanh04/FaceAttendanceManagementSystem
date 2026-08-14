from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from src.api.v1.features.corrections import schemas
from src.api.v1.features.corrections.service import (
    CorrectionService,
    get_correction_service,
)
from src.api.v1.features.staff.models import Employee
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import RoleName
from src.core.dependencies.auth import get_current_employee, require_roles

router = APIRouter(prefix="/corrections", tags=["Corrections"])


@router.get("/requests", response_model=schemas.CorrectionListResponse)
async def list_correction_requests(
    query: schemas.CorrectionListQuery = Depends(),
    service: CorrectionService = Depends(get_correction_service),
    current_user: User = Depends(
        require_roles(RoleName.admin, RoleName.hr, RoleName.manager, RoleName.employee)
    ),
) -> schemas.CorrectionListResponse:
    return await service.list_correction_requests(
        query=query,
        current_user=current_user,
    )


@router.post(
    "/requests",
    response_model=schemas.AttendanceCorrectionRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_correction_request(
    payload: schemas.AttendanceCorrectionRequestCreate,
    service: CorrectionService = Depends(get_correction_service),
    _: User = Depends(require_roles(RoleName.employee)),
    current_employee: Employee = Depends(get_current_employee),
) -> schemas.AttendanceCorrectionRequestRead:
    return await service.create_correction_request(
        employee_id=current_employee.employee_id,
        payload=payload,
    )


@router.get(
    "/requests/{request_id}",
    response_model=schemas.AttendanceCorrectionRequestRead,
)
async def get_correction_request(
    request_id: uuid.UUID,
    service: CorrectionService = Depends(get_correction_service),
    current_user: User = Depends(
        require_roles(RoleName.admin, RoleName.hr, RoleName.manager, RoleName.employee)
    ),
) -> schemas.AttendanceCorrectionRequestRead:
    return await service.get_correction_request(
        request_id=request_id,
        current_user=current_user,
    )


@router.patch(
    "/requests/{request_id}",
    response_model=schemas.AttendanceCorrectionRequestRead,
)
async def update_pending_correction_request(
    request_id: uuid.UUID,
    payload: schemas.AttendanceCorrectionRequestUpdate,
    service: CorrectionService = Depends(get_correction_service),
    _: User = Depends(require_roles(RoleName.employee)),
    current_employee: Employee = Depends(get_current_employee),
) -> schemas.AttendanceCorrectionRequestRead:
    return await service.update_pending_correction_request(
        request_id=request_id,
        payload=payload,
        employee_id=current_employee.employee_id,
    )


@router.post(
    "/requests/{request_id}/cancel",
    response_model=schemas.AttendanceCorrectionRequestRead,
)
async def cancel_correction_request(
    request_id: uuid.UUID,
    service: CorrectionService = Depends(get_correction_service),
    _: User = Depends(require_roles(RoleName.employee)),
    current_employee: Employee = Depends(get_current_employee),
) -> schemas.AttendanceCorrectionRequestRead:
    return await service.cancel_correction_request(
        request_id=request_id,
        employee_id=current_employee.employee_id,
    )


@router.post(
    "/requests/{request_id}/review",
    response_model=schemas.AttendanceCorrectionRequestRead,
)
async def review_correction_request(
    request_id: uuid.UUID,
    payload: schemas.ReviewCorrectionRequest,
    service: CorrectionService = Depends(get_correction_service),
    current_user: User = Depends(
        require_roles(RoleName.manager, RoleName.hr, RoleName.admin)
    ),
    current_employee: Employee = Depends(get_current_employee),
) -> schemas.AttendanceCorrectionRequestRead:
    return await service.review_correction_request(
        request_id=request_id,
        payload=payload,
        reviewer_id=current_employee.employee_id,
        reviewer_role=current_user.role_name,
        current_user=current_user,
    )


@router.get(
    "/requests/{request_id}/logs",
    response_model=list[schemas.AttendanceCorrectionLogRead],
)
async def list_correction_request_logs(
    request_id: uuid.UUID,
    service: CorrectionService = Depends(get_correction_service),
    current_user: User = Depends(
        require_roles(RoleName.admin, RoleName.hr, RoleName.manager, RoleName.employee)
    ),
) -> list[schemas.AttendanceCorrectionLogRead]:
    return await service.list_correction_request_logs(
        request_id=request_id,
        current_user=current_user,
    )
