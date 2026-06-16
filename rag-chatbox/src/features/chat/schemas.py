from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    user_role: str = Field(..., min_length=1)


class ChatCitation(BaseModel):
    index: int
    chunk_id: str
    document_id: str | None = None
    filename: str
    page: int | None = None
    section: str | None = None
    clause_number: str | None = None
    score: float
    file_path: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation] = []
    low_confidence: bool = False
    used_context: bool = False
