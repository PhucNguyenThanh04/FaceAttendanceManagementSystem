from __future__ import annotations

from datetime import datetime

import httpx
from pydantic import ValidationError

from src.integrations.api_service.clients import APIServiceClient
from src.integrations.api_service.schemas import AttendanceEventListQuery
from src.tools.api_queries.errors import format_api_error
from src.tools.api_queries.formatters import format_attendance_events
from src.tools.api_queries.schemas import AttendanceQueryInput
from src.tools.base_tool import BaseTool
from src.utils.enums import AttendanceEventType


class AttendanceQueryTool(BaseTool):
    name = "attendance_query"
    description = (
        "Tra cứu lịch sử attendance event của nhân viên hiện tại từ api-service. "
        "Dùng khi user hỏi lịch sử check-in/check-out, event hợp lệ/bị từ chối, "
        "hoặc các event trong một khoảng thời gian. "
        "Không nhận employee_id từ LLM và không truy vấn nhân viên khác."
    )
    args_schema = AttendanceQueryInput

    def __init__(
        self,
        api_service_client: APIServiceClient,
        employee_id: str,
        user_role: str,
    ) -> None:
        self.api_service_client = api_service_client
        self.employee_id = employee_id
        self.user_role = user_role

    async def run(
        self,
        page: int = 1,
        page_size: int = 20,
        event_type: AttendanceEventType | None = None,
        accepted: bool | None = None,
        event_time_from: datetime | None = None,
        event_time_to: datetime | None = None,
    ) -> str:
        try:
            query = AttendanceEventListQuery(
                page=page,
                page_size=page_size,
                employee_id=self.employee_id,
                event_type=event_type,
                accepted=accepted,
                event_time_from=event_time_from,
                event_time_to=event_time_to,
            )
            events = await self.api_service_client.list_attendance_events(query)
        except (ValidationError, httpx.HTTPError) as exc:
            return format_api_error(exc)

        return format_attendance_events(events, query)
