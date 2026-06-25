from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from src.integrations.api_service.clients import APIServiceClient
from src.integrations.api_service.schemas import (
    AttendanceEventListQuery,
    AttendanceEventRead,
    CurrentShiftRead,
    EmployeeRead,
)
from src.tools.base_tool import BaseTool


class DatabaseQueryTool(BaseTool):
    name = "database_query"
    description = (
        "Tra cứu dữ liệu vận hành từ api-service. "
        "Dùng operation=get_employee, get_current_shift hoặc list_attendance_events. "
        "Tool này chỉ đọc dữ liệu của nhân viên hiện tại, không tạo/sửa/xóa dữ liệu."
    )

    def __init__(self, api_service_client: APIServiceClient, employee_id: str) -> None:
        self.api_service_client = api_service_client
        self.employee_id = employee_id

    async def run(self, operation: str | None = None, **kwargs: Any) -> str:
        if not operation:
            return (
                "Thiếu operation. "
                "Các operation hợp lệ: get_employee, get_current_shift, list_attendance_events."
            )

        operation = self._normalize_operation(operation)

        try:
            if operation == "get_employee":
                return await self._get_employee(kwargs)
            if operation == "get_current_shift":
                return await self._get_current_shift(kwargs)
            if operation == "list_attendance_events":
                return await self._list_attendance_events(kwargs)
        except (ValueError, ValidationError) as exc:
            return f"Tham số truy vấn không hợp lệ: {exc}"
        except httpx.HTTPStatusError as exc:
            return (
                "api-service trả lỗi khi truy vấn dữ liệu: "
                f"status={exc.response.status_code}, body={exc.response.text}"
            )
        except httpx.HTTPError as exc:
            return f"Không gọi được api-service: {exc}"

        return (
            "Operation không được hỗ trợ. "
            "Các operation hợp lệ: get_employee, get_current_shift, list_attendance_events."
        )

    async def _get_employee(self, kwargs: dict[str, Any]) -> str:
        employee = await self.api_service_client.get_employee(self.employee_id)
        return self._format_employee(employee)

    async def _get_current_shift(self, kwargs: dict[str, Any]) -> str:
        as_of = self._parse_date(kwargs.get("as_of"), "as_of")
        current_shift = await self.api_service_client.get_employee_current_shift(
            employee_id=self.employee_id,
            as_of=as_of,
        )
        return self._format_current_shift(current_shift)

    async def _list_attendance_events(self, kwargs: dict[str, Any]) -> str:
        payload = self._build_attendance_event_query_payload(kwargs)
        query = AttendanceEventListQuery.model_validate(payload)
        events = await self.api_service_client.list_attendance_events(query)
        return self._format_attendance_events(events, query)

    @staticmethod
    def _normalize_operation(operation: str) -> str:
        normalized = operation.strip().lower().replace("-", "_")
        aliases = {
            "employee": "get_employee",
            "get_employee_by_id": "get_employee",
            "current_shift": "get_current_shift",
            "employee_current_shift": "get_current_shift",
            "attendance_events": "list_attendance_events",
            "list_events": "list_attendance_events",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _parse_date(value: Any, field_name: str) -> date | None:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError(f"{field_name} phải có dạng YYYY-MM-DD") from exc

    def _build_attendance_event_query_payload(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        raw_query = kwargs.get("query")
        payload = dict(raw_query) if isinstance(raw_query, dict) else {}

        allowed_fields = {
            "page",
            "page_size",
            "event_type",
            "accepted",
            "event_time_from",
            "event_time_to",
        }
        for field in allowed_fields:
            if field in kwargs and kwargs[field] is not None:
                payload[field] = kwargs[field]

        payload["employee_id"] = self.employee_id
        return payload

    @staticmethod
    def _format_employee(employee: EmployeeRead) -> str:
        return "\n".join(
            [
                "Hồ sơ nhân viên:",
                f"- employee_id: {employee.employee_id}",
                f"- employee_code: {employee.employee_code}",
                f"- full_name: {employee.full_name}",
                f"- status: {employee.status.value}",
                f"- department_id: {employee.department_id}",
                f"- position_id: {employee.position_id}",
                f"- manager_id: {employee.manager_id}",
                f"- phone: {employee.phone}",
                f"- hire_date: {employee.hire_date}",
                f"- resignation_date: {employee.resignation_date}",
            ]
        )

    @staticmethod
    def _format_current_shift(current_shift: CurrentShiftRead) -> str:
        shift = current_shift.shift
        code = f" ({shift.code})" if shift.code else ""
        overnight = "qua đêm" if shift.is_overnight else "trong ngày"
        return "\n".join(
            [
                "Ca làm của nhân viên:",
                f"- employee_id: {current_shift.employee_id}",
                f"- assignment_id: {current_shift.assignment_id}",
                f"- effective_date: {current_shift.effective_date}",
                f"- end_date: {current_shift.end_date}",
                f"- shift: {shift.name}{code}",
                f"- time: {shift.start_time} - {shift.end_time} ({overnight})",
                f"- late_threshold_minutes: {shift.late_threshold_minutes}",
                f"- early_leave_threshold_minutes: {shift.early_leave_threshold_minutes}",
                f"- required_work_minutes: {shift.required_work_minutes}",
            ]
        )

    @staticmethod
    def _format_attendance_events(
        events: list[AttendanceEventRead],
        query: AttendanceEventListQuery,
    ) -> str:
        if not events:
            return "Không tìm thấy attendance event phù hợp với bộ lọc."

        lines = [
            "Danh sách attendance event:",
            f"- page: {query.page}",
            f"- page_size: {query.page_size}",
            f"- returned: {len(events)}",
        ]

        max_events_to_show = 30
        for index, event in enumerate(events[:max_events_to_show], start=1):
            accepted = "accepted" if event.is_accepted else "rejected"
            lines.extend(
                [
                    "",
                    f"[{index}] event_id: {event.event_id}",
                    f"- employee_id: {event.employee_id}",
                    f"- event_type: {event.event_type.value}",
                    f"- event_time: {event.event_time}",
                    f"- status: {accepted}",
                    f"- rejection_reason: {event.rejection_reason}",
                ]
            )

        if len(events) > max_events_to_show:
            lines.append(f"\nCòn {len(events) - max_events_to_show} event chưa hiển thị.")

        return "\n".join(lines)
