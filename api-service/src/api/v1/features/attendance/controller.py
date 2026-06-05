from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends

from src.api.v1.features.attendance import schemas
from src.api.v1.features.attendance.service import (
    AttendanceService,
    get_attendance_service,
)
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import AttendanceEventType, RoleName
from src.core.dependencies.auth import require_roles

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/events", response_model=schemas.AttendanceEventAcceptedResponse)
async def create_attendance_event(
    payload: schemas.AttendanceAIEventCreate,
    service: AttendanceService = Depends(get_attendance_service),
) -> schemas.AttendanceEventAcceptedResponse:
    return await service.create_event_from_ai(payload)


@router.get("/events", response_model=list[schemas.AttendanceEventRead])
async def list_attendance_events(
    page: int = 1,
    page_size: int = 20,
    employee_id: uuid.UUID | None = None,
    event_type: AttendanceEventType | None = None,
    accepted: bool | None = None,
    event_time_from: datetime | None = None,
    event_time_to: datetime | None = None,
    service: AttendanceService = Depends(get_attendance_service),
    _: User = Depends(require_roles(RoleName.admin, RoleName.hr, RoleName.manager)),
) -> list[schemas.AttendanceEventRead]:
    query = schemas.AttendanceEventListQuery(
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        event_type=event_type,
        accepted=accepted,
        event_time_from=event_time_from,
        event_time_to=event_time_to,
    )
    return await service.list_events(query)


@router.get("/events/{event_id}", response_model=schemas.AttendanceEventRead)
async def get_attendance_event(
    event_id: uuid.UUID,
    service: AttendanceService = Depends(get_attendance_service),
    _: User = Depends(require_roles(RoleName.admin, RoleName.hr, RoleName.manager)),
) -> schemas.AttendanceEventRead:
    return await service.get_event(event_id)
