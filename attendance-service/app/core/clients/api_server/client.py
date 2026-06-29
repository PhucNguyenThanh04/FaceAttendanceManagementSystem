from __future__ import annotations

from typing import Any

import httpx

from app.core.clients.api_server.schemas import (
    APIAttendanceEventCreate,
    APIAttendanceEventResponse,
    APIHealthResponse,
    APIServerPaths,
)
from app.core.configs.settings import settings
from app.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class ApiServerClient:
    """Small HTTP client used by attendance-service to call api-service."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client
        self._api_key = settings.api_key
        self._default_headers = {"Attendance-API-Key": self._api_key} if self._api_key else {}

    async def health(self) -> APIHealthResponse:
        data = await self._request_json("GET", APIServerPaths.HEALTH, require_api_key=False)
        return APIHealthResponse.model_validate(data)

    async def record_attendance(
        self,
        payload: APIAttendanceEventCreate,
    ) -> APIAttendanceEventResponse:
        data = await self._request_json(
            "POST",
            APIServerPaths.ATTENDANCE_EVENTS,
            json=payload.model_dump(mode="json", exclude_none=True),
            require_api_key=True,
        )
        return APIAttendanceEventResponse.model_validate(data)

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        require_api_key: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        headers = dict(kwargs.pop("headers", {}))
        if require_api_key:
            headers.update(self._default_headers)

        try:
            response = await self._http.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "api-service returned error: method=%s path=%s status=%s body=%s",
                method,
                path,
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.HTTPError:
            logger.exception("api-service request failed: method=%s path=%s", method, path)
            raise

        logger.debug(
            "api-service response: method=%s path=%s status=%s body=%s",
            method,
            path,
            response.status_code,
            response.text,
        )
        return response.json()
