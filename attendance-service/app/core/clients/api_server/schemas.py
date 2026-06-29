from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class APIServerPaths:
    HEALTH = "/health"
    ATTENDANCE_EVENTS = "/api/v1/attendance/events"
    ATTENDANCE_CHECK = ATTENDANCE_EVENTS


class APIAttendanceEventCreate(BaseModel):
    """Payload attendance-service sends to api-service after stable face recognition."""

    employee_id: UUID = Field(..., description="employees.employee_id in api-service")
    event_time: datetime | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    anti_spoof_score: float | None = Field(default=None, ge=0.0, le=1.0)
    image_url: str | None = Field(default=None, max_length=500)
    raw_result: dict[str, Any] | None = None


class APIAttendanceEventResponse(BaseModel):
    """Result returned by api-service after applying attendance business rules."""

    accepted: bool
    reason: str | None = None
    employee_id: UUID
    event_id: UUID | None = None
    record_id: UUID | None = None
    event_type: str | None = None
    event_time: datetime
    work_date: date | None = None
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    late_minutes: int | None = None
    early_leave_minutes: int | None = None
    worked_minutes: int | None = None
    status: str | None = None
    cooldown_ttl_seconds: int | None = None


# Backward-compatible aliases for older imports.
APIAttendanceCheckRequest = APIAttendanceEventCreate
APIAttendanceCheckResponse = APIAttendanceEventResponse


class APIHealthResponse(BaseModel):
    status: str
    detail: str | None = None
