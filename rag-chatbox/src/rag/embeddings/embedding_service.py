from __future__ import annotations

import asyncio

from src.rag.embeddings.embedding_client import EmbeddingBatch, EmbeddingClient


class EmbeddingService:
    """
    Async business logic layer cho embedding.
    Biết về use case — không biết model là gì.

    Mọi call đều non-blocking: chạy EmbeddingClient sync methods
    trong thread pool executor để không block FastAPI event loop.
    """

    def __init__(self, client: EmbeddingClient) -> None:
        self._client = client


    async def embed_query(self, query: str) -> list[float]:
        """Dense embedding cho 1 query — dùng trong hybrid search."""
        results = await asyncio.to_thread(self._client.embed_dense, [query])
        return results[0]

    async def embed_query_hybrid(self, query: str) -> EmbeddingBatch:
        """Dense + sparse embedding cho 1 query — dùng trong hybrid search."""
        return await asyncio.to_thread(self._client.embed_hybrid, [query])

    # ------------------------------------------------------------------
    # Ingestion path — encode batch documents
    # ------------------------------------------------------------------

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Dense embedding cho batch documents."""
        return await asyncio.to_thread(self._client.embed_dense, texts)

    async def embed_document_batch(self, texts: list[str]) -> EmbeddingBatch:
        """Dense + sparse embedding cho batch documents."""
        return await asyncio.to_thread(self._client.embed_hybrid, texts)