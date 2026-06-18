from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from src.rag.ingestion.pipeline import IngestionPipeline
from src.rag.embeddings.embedding_service import EmbeddingService
from src.integrations.qdrant.store import QdrantVectorStore
from src.rag.retrieval.reranker import RerankerService

from src.core.settings import get_settings

settings = get_settings()

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")


def get_embedding_service(request: Request) -> EmbeddingService:
    return request.app.state.embedding_service


def get_vector_store(request: Request) -> QdrantVectorStore:
    return request.app.state.vector_store


def get_reranker_service(request: Request) -> RerankerService:
    return request.app.state.reranker_service


def get_ingestion_pipeline(request: Request) -> IngestionPipeline:
    return request.app.state.ingestion_pipeline
