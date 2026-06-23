from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from src.api.v1.features.attendance import schemas
from src.api.v1.features.attendance.service import (
    AttendanceService,
    get_attendance_read_service,
    get_attendance_service,
)
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import RoleName
from src.core.dependencies.auth import (
require_roles, 
verify_api_key_attendance, 
get_current_user_or_rag_api_key
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post(
    "/events",
    response_model=schemas.AttendanceEventAcceptedResponse,
    dependencies=[Depends(verify_api_key_attendance)],
)
async def create_attendance_event(
    payload: schemas.AttendanceAIEventCreate,
    service: AttendanceService = Depends(get_attendance_service),
) -> schemas.AttendanceEventAcceptedResponse:
    return await service.create_event_from_ai(payload)


@router.get("/events", response_model=list[schemas.AttendanceEventRead])
async def list_attendance_events(
    query: schemas.AttendanceEventListQuery ,
    service: AttendanceService = Depends(get_attendance_read_service),
    _: User = Depends(get_current_user_or_rag_api_key),
) -> list[schemas.AttendanceEventRead]:
    return await service.list_events(query)


@router.get("/events/{event_id}", response_model=schemas.AttendanceEventRead)
async def get_attendance_event(
    event_id: uuid.UUID,
    service: AttendanceService = Depends(get_attendance_read_service),
    _: User = Depends(require_roles(RoleName.admin, RoleName.hr, RoleName.manager)),
) -> schemas.AttendanceEventRead:
    return await service.get_event(event_id)
