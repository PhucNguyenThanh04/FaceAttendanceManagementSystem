from typing import Literal
from pydantic import BaseModel
from datetime import datetime, timezone


EMBEDDING_VERSION = "insightface-buffalo_l-v1"


class PayloadCreateRequest(BaseModel):
    staff_id: str
    face_profile_id: str        # UUID do API server tạo, dùng để map với PostgreSQL
    employee_code: str
    embedding_version: str = EMBEDDING_VERSION
    is_active: bool = True
    created_at: str | None = None   # AI server tự set nếu None
    updated_at: str | None = None   # AI server tự set nếu None


# ── Update ────────────────────────────────────────────────────────────────────

class PayloadUpdateRequest(BaseModel):
    employee_code: str | None = None
    is_active: bool | None = None
    updated_at: str | None = None


# ── Search response ───────────────────────────────────────────────────────────

class PayloadSearchResponse(BaseModel):
    staff_id: str
    face_profile_id: str
    employee_code: str
    embedding_version: str
    is_active: bool = True
    created_at: str
    updated_at: str | None = None
    score: float
    qdrant_id: str


# ── Identify response ─────────────────────────────────────────────────────────

class PayloadIdentifyResponse(BaseModel):
    status: Literal["recognized", "unknown", "ambiguous"]
    person: PayloadSearchResponse | None
    votes: int | None = None
    total: int | None = None
    confidence: float | None = None
