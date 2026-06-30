import logging

from fastapi import APIRouter, Depends, HTTPException

from src.core.dependenci import verify_api_key
from src.features.chat.schemas import ChatRequest, ChatResponse
from src.features.chat.service import ChatService, get_chat_service


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["Chat"], dependencies=[Depends(verify_api_key)])


@router.post("/message", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        return await chat_service.chat(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Unhandled error in chat endpoint: conversation_id=%s employee_id=%s",
            request.conversation_id,
            request.employee_id,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
