import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.utils.datetime_utils import AppTimezoneModel
from src.utils.enums import AttendanceEventType, EmployeeStatus


class APIServerPaths:
    EMPLOYEE_BY_ID = "/api/v1/employees/{employee_id}"
    EMPLOYEE_CURRENT_SHIFT = "/api/v1/employees/{employee_id}/current-shift"
    ATTENDANCE_EVENTS = "/api/v1/attendance/events"


class EmployeeRead(AppTimezoneModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: uuid.UUID
    user_id: uuid.UUID | None = None
    registered_by: uuid.UUID | None = None
    employee_code: str
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    department_id: int | None = None
    position_id: int | None = None
    manager_id: uuid.UUID | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None
    hire_date: date | None = None
    resignation_date: date | None = None
    status: EmployeeStatus
    created_at: datetime
    updated_at: datetime


class WorkShiftRead(AppTimezoneModel):
    model_config = ConfigDict(from_attributes=True)

    shift_id: int
    name: str
    code: str | None = None
    start_time: time
    end_time: time
    is_overnight: bool = False
    late_threshold_minutes: int = 0
    early_leave_threshold_minutes: int = 0
    required_work_minutes: int | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class CurrentShiftRead(BaseModel):
    assignment_id: int
    employee_id: uuid.UUID
    effective_date: date
    end_date: date | None = None
    shift: WorkShiftRead


# attendance event
class AttendanceEventListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    employee_id: uuid.UUID | None = None
    event_type: AttendanceEventType | None = None
    accepted: bool | None = None
    event_time_from: datetime | None = None
    event_time_to: datetime | None = None

    @model_validator(mode="after")
    def validate_time_window(self) -> "AttendanceEventListQuery":
        if self.event_time_from and self.event_time_to and self.event_time_to < self.event_time_from:
            raise ValueError("event_time_to must be on/after event_time_from")
        return self


class AttendanceEventBase(AppTimezoneModel):
    employee_id: uuid.UUID | None = None
    event_type: AttendanceEventType
    event_time: datetime
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    anti_spoof_score: float | None = Field(default=None, ge=0, le=1)
    image_url: str | None = Field(default=None, max_length=500)
    raw_result: dict | None = None
    is_accepted: bool = True
    rejection_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_rejection_reason(self) -> "AttendanceEventBase":
        if not self.is_accepted and not self.rejection_reason:
            raise ValueError("rejection_reason is required when is_accepted=False")
        return self


class AttendanceEventRead(AttendanceEventBase):
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    created_at: datetime
