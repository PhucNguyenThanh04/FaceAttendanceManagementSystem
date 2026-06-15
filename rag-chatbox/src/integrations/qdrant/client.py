from __future__ import annotations

from collections.abc import Sequence

from qdrant_client import QdrantClient, models

from src.core.settings import settings


DENSE_VECTOR_NAME = settings.dense_vector_name
SPARSE_VECTOR_NAME = settings.sparse_vector_name


class QdrantClientManager:
    """
    Owns the Qdrant connection and collection schema.

    Higher layers should not create collections or know vector names directly;
    they should receive a QdrantVectorStore backed by this client.
    """

    def __init__(
        self,
        url: str | None = None,
        timeout: float | None = None,
        dense_vector_size: int = settings.bge_m3_dense_size,
        dense_vector_name: str = settings.dense_vector_name,
        sparse_vector_name: str = settings.sparse_vector_name,
    ) -> None:
        self._client = QdrantClient(
            url=url or settings.qdrant_url,
            timeout=timeout or settings.qdrant_timeout,
        )
        self.dense_vector_size = dense_vector_size
        self.dense_vector_name = dense_vector_name
        self.sparse_vector_name = sparse_vector_name

    def get_client(self) -> QdrantClient:
        return self._client

    def ensure_collection(self, collection_name: str) -> None:
        if self._collection_exists(collection_name):
            return

        self._client.create_collection(
            collection_name=collection_name,
            vectors_config={
                self.dense_vector_name: models.VectorParams(
                    size=self.dense_vector_size,
                    distance=models.Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                self.sparse_vector_name: models.SparseVectorParams(),
            },
        )

    def ensure_default_collections(self) -> None:
        self.ensure_collections(
            [
                settings.qdrant_collection_policy,
                settings.qdrant_collection_law,
            ]
        )

    def ensure_collections(self, collection_names: Sequence[str]) -> None:
        for collection_name in collection_names:
            self.ensure_collection(collection_name)

    def _collection_exists(self, collection_name: str) -> bool:
        if hasattr(self._client, "collection_exists"):
            return bool(self._client.collection_exists(collection_name))

        try:
            self._client.get_collection(collection_name)
        except Exception:
            return False
        return True
