from typing import Literal
from pydantic import BaseModel
from datetime import datetime, timezone


EMBEDDING_VERSION = "insightface-buffalo_l-v1"


# ── Create ────────────────────────────────────────────────────────────────────

class PayloadCreateRequest(BaseModel):
    staff_id: str
    face_profile_id: str        # UUID do API server tạo, dùng để map với PostgreSQL
    username: str
    status: str = "active"
    embedding_version: str = EMBEDDING_VERSION
    created_at: str | None = None   # AI server tự set nếu None


# ── Update ────────────────────────────────────────────────────────────────────

class PayloadUpdateRequest(BaseModel):
    username: str | None = None
    status: str | None = None


# ── Search response ───────────────────────────────────────────────────────────

class PayloadSearchResponse(BaseModel):
    staff_id: str
    face_profile_id: str
    username: str
    status: str
    embedding_version: str
    created_at: str
    score: float
    qdrant_id: str


# ── Identify response ─────────────────────────────────────────────────────────

class PayloadIdentifyResponse(BaseModel):
    status: Literal["recognized", "unknown", "ambiguous"]
    person: PayloadSearchResponse | None
    votes: int | None = None
    total: int | None = None
    confidence: float | None = None

