from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AttendanceRecognitionRequest(BaseModel):
    """
    Payload attendance-service sends to api-service after a stable face recognition.

    api-service owns the attendance business rules, so this request only
    describes what attendance-service recognized from the camera/Qdrant pipeline.
    """

    employee_id: UUID = Field(..., description="employees.employee_id from api-service")
    employee_code: str = Field(..., description="Human-readable employee code")
    recognized_at: datetime = Field(..., description="Recognition timestamp")

    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Final recognition confidence from vector search",
    )
    anti_spoof_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Anti-spoofing score if available",
    )

    face_profile_id: UUID | None = Field(
        default=None,
        description="face_profiles.profile_id from api-service",
    )
    qdrant_id: str | None = Field(
        default=None,
        description="Matched point id in Qdrant",
    )
    camera_id: str | None = Field(
        default=None,
        description="Logical camera identifier",
    )
    image_url: str | None = Field(
        default=None,
        description="Optional evidence image URL if attendance-service stores snapshots",
    )
    raw_result: dict[str, Any] | None = Field(
        default=None,
        description="Extra debug metadata from attendance-service",
    )


class AttendanceRecognitionResponse(BaseModel):
    """
    Response expected from api-service after applying attendance business rules.
    """

    success: bool
    employee_id: UUID | None = None
    employee_code: str | None = None
    full_name: str | None = None

    action: Literal["check_in", "check_out", "none"] | None = None
    reason: Literal[
        "cooldown",
        "employee_not_found",
        "employee_inactive",
        "invalid_payload",
        "rejected",
        "server_error",
    ] | None = None

    checked_at: datetime | None = None
    cooldown_until: datetime | None = None
    message: str
