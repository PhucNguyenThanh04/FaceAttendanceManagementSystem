from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.settings import get_settings
from src.core.setup_logging import setup_logger
from src.integrations.qdrant.client import QdrantClientManager
from src.integrations.qdrant.store import QdrantVectorStore
from src.rag.embeddings.embedding_client import EmbeddingClient
from src.rag.embeddings.embedding_service import EmbeddingService
from src.rag.ingestion.chunkers.legachunker import LegalStructureAwareChunker
from src.rag.ingestion.indexer import DocumentIndexer
from src.rag.ingestion.loaders.factory_loader import LoaderFactory
from src.rag.ingestion.pipeline import IngestionPipeline
from src.rag.retrieval.reranker import RerankerClient, RerankerService

settings = get_settings()

logger = setup_logger(
    __name__,
    level=logging.DEBUG if settings.api_debug else logging.INFO,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up RAG service...")

    # --- Embedding ---
    client = EmbeddingClient()
    embedding_service = EmbeddingService(client)
    logger.info("Warming up embedding model on device: %s", client.device)
    await embedding_service.warmup()
    logger.info("Embedding model warmup completed")

    # --- Qdrant ---
    qdrant_manager = QdrantClientManager()
    await qdrant_manager.ensure_collection(settings.default_qdrant_collection)
    vector_store = QdrantVectorStore(qdrant_manager.get_client())

    # --- Reranker ---
    reranker_client = RerankerClient()
    reranker_service = RerankerService(reranker_client)
    logger.info("Warming up reranker model on device: %s", reranker_client.device)
    await reranker_service.warmup()
    logger.info("Reranker model warmup completed")

    # --- Ingestion pipeline ---
    ingestion_pipeline = IngestionPipeline(
        loader=LoaderFactory,
        chunker=LegalStructureAwareChunker(),
        indexer=DocumentIndexer(embedding_service, vector_store),
        qdrant_manager=qdrant_manager,
    )
    
    # Lưu services lên app.state để routes/DI dùng:
    app.state.embedding_service = embedding_service
    app.state.vector_store = vector_store
    app.state.reranker_service = reranker_service
    app.state.ingestion_pipeline = ingestion_pipeline
    app.state.qdrant_manager = qdrant_manager

    logger.info("RAG service ready")

    yield

    logger.info("Shutting down RAG service")
    await qdrant_manager.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agentic RAG — Attendance System",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.api_debug,
    )

    from src.api.v1.routers import router as v1_router
    app.include_router(v1_router)

    return app


app = create_app()


@app.get("/health")
async def health_check():
    return {"status": "ok"}
