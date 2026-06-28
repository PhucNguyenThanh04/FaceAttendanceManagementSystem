from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.utils.enums import AttendanceEventType


class EmployeeQueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShiftQueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: date | None = Field(
        default=None,
        description="Ngày cần tra cứu ca làm, định dạng YYYY-MM-DD. Bỏ trống để lấy ca hiện tại.",
    )


class AttendanceQueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    event_type: AttendanceEventType | None = Field(
        default=None,
        description="Loại sự kiện attendance: check_in, check_out hoặc unknown.",
    )
    accepted: bool | None = Field(
        default=None,
        description="true để lấy event hợp lệ, false để lấy event bị từ chối.",
    )
    event_time_from: datetime | None = Field(
        default=None,
        description="Thời điểm bắt đầu lọc event, dạng ISO datetime.",
    )
    event_time_to: datetime | None = Field(
        default=None,
        description="Thời điểm kết thúc lọc event, dạng ISO datetime.",
    )

    @model_validator(mode="after")
    def validate_time_window(self) -> "AttendanceQueryInput":
        if (
            self.event_time_from
            and self.event_time_to
            and self.event_time_to < self.event_time_from
        ):
            raise ValueError("event_time_to must be on/after event_time_from")
        return self
