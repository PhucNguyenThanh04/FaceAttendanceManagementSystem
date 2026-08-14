from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from src.api.v1.shared.enums import AttendanceRecordStatus, AttendanceSource


class MonthlyReportQuery(BaseModel):
    year: int = Field(default_factory=lambda: date.today().year, ge=1900, le=9998)
    month: int = Field(default_factory=lambda: date.today().month, ge=1, le=12)
    department_id: int | None = Field(default=None, ge=1)


class LeaveSummaryQuery(BaseModel):
    year: int = Field(default_factory=lambda: date.today().year, ge=1900, le=9998)
    month: int | None = Field(default=None, ge=1, le=12)
    department_id: int | None = Field(default=None, ge=1)


class LateRankingQuery(MonthlyReportQuery):
    limit: int = Field(default=20, ge=1, le=200)


class EmployeeMonthlyReportQuery(BaseModel):
    year: int = Field(default_factory=lambda: date.today().year, ge=1900, le=9998)
    month: int = Field(default_factory=lambda: date.today().month, ge=1, le=12)


class AttendanceSummaryRead(BaseModel):
    department_id: int
    department_name: str
    employee_count: int
    total_records: int
    present_days: int
    late_days: int
    early_leave_days: int
    absent_days: int
    on_leave_days: int
    holiday_days: int
    missing_check_in_days: int
    missing_check_out_days: int
    total_worked_minutes: int
    total_late_minutes: int
    total_early_leave_minutes: int


class LeaveSummaryRead(BaseModel):
    department_id: int
    department_name: str
    employee_count: int
    total_requests: int
    pending_requests: int
    approved_requests: int
    rejected_requests: int
    cancelled_requests: int
    approved_leave_days: float


class LateRankingRead(BaseModel):
    rank: int
    employee_id: uuid.UUID
    employee_code: str
    full_name: str
    department_id: int | None = None
    department_name: str | None = None
    late_days: int
    total_late_minutes: int
    average_late_minutes: float


class MonthlyAttendanceDayRead(BaseModel):
    record_id: uuid.UUID
    work_date: date
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    status: AttendanceRecordStatus
    late_minutes: int
    early_leave_minutes: int
    worked_minutes: int
    source: AttendanceSource
    notes: str | None = None


class EmployeeMonthlyReportRead(BaseModel):
    employee_id: uuid.UUID
    employee_code: str
    full_name: str
    department_id: int | None = None
    department_name: str | None = None
    year: int
    month: int
    total_records: int
    present_days: int
    late_days: int
    early_leave_days: int
    absent_days: int
    on_leave_days: int
    holiday_days: int
    missing_check_in_days: int
    missing_check_out_days: int
    total_worked_minutes: int
    total_late_minutes: int
    total_early_leave_minutes: int
    records: list[MonthlyAttendanceDayRead]
