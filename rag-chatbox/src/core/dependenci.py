from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from src.rag.embeddings.embedding_service import EmbeddingService

from src.core.settings import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")


def get_embedding_service(request: Request) -> EmbeddingService:
    return request.app.state.embedding_service
