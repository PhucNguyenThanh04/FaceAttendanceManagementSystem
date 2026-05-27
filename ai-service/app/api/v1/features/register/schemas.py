# features/register/schemas.py — schema riêng của feature này

from pydantic import BaseModel
from typing import Optional
from app.core.vector_db.schemas import PayloadCreateRequest

class AddPhotoResponse(BaseModel):
    accepted: bool
    reason: Optional[str] = None
    count: Optional[int] = None
    quality_score: Optional[float] = None


class CommitRequest(BaseModel):
    session_id: str
    payload: PayloadCreateRequest   # gom session_id + payload vào 1 body


class CommitResponse(BaseModel):
    success: bool
    staff_id: str
    face_profile_id: str
    vectors_stored: int