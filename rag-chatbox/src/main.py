from __future__ import annotations


from contextlib import asynccontextmanager

from fastapi import FastAPI
import logging

from src.rag.embeddings.embedding_service import EmbeddingService
from src.rag.embeddings.embedding_client import EmbeddingClient
from src.core.settings import settings
from src.core.setup_logging import setup_logger

logger = setup_logger(__name__, level=logging.DEBUG if settings.debug else logging.INFO)



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up RAG service...")


    client = EmbeddingClient()
    embedding_service = EmbeddingService(client)

    app.state.embedding_service = embedding_service
    logger.info("Embedding service initialized")


    logger.info("RAG service ready")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agentic RAG — Attendance System",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.api_debug,
    )

    # Register routers
    # from src.api.v1.routers import router as v1_router
    # app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()


@app.get("/health")
async def health_check():
    return {"status": "ok"}
