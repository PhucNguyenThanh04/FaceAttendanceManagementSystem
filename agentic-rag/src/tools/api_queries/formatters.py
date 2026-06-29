from __future__ import annotations

from src.integrations.api_service.schemas import (
    AttendanceEventListQuery,
    AttendanceEventRead,
    CurrentShiftRead,
    EmployeeRead,
)


def format_employee(employee: EmployeeRead) -> str:
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


def format_current_shift(current_shift: CurrentShiftRead) -> str:
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


def format_attendance_events(
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
