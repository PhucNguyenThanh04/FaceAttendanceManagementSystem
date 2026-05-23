from typing import Literal

from pydantic import BaseModel


class PayloadCreateRequest(BaseModel):
    staff_id: str
    username: str
    fullname: str
    position: str
    phongban: str
    is_active: bool = True
    created_at: str | None = None


class PayloadUpdateRequest(BaseModel):
    username: str | None = None
    fullname: str | None = None
    position: str | None = None
    phongban: str | None = None
    is_active: bool | None = None


class PayloadSearchResponse(BaseModel):
    staff_id: str
    username: str
    fullname: str
    position: str
    phongban: str
    is_active: bool
    created_at: str
    score: float
    qdrant_id: str


class PayloadIdentifyResponse(BaseModel):
    status: Literal["recognized", "unknown", "ambiguous"]
    person: PayloadSearchResponse | None
    votes: int | None = None
    total: int | None = None
    confidence: float | None = None
