from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from src.integrations.qdrant.client import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from src.rag.ingestion.chunkers.base_chunker import DocumentChunk

from src.core.settings import settings
from src.core.setup_logging import setup_logger

logger = setup_logger(__name__)


@dataclass
class QdrantSearchResult:
    point_id: str
    score: float
    content: str
    metadata: dict[str, Any]
    payload: dict[str, Any]


class QdrantVectorStore:

    def __init__(
        self,
        client: QdrantClient,
        dense_vector_name: str = DENSE_VECTOR_NAME,
        sparse_vector_name: str = SPARSE_VECTOR_NAME,
    ) -> None:
        self.client = client
        self.dense_vector_name = dense_vector_name
        self.sparse_vector_name = sparse_vector_name

    def upsert_chunks(
        self,
        collection_name: str,
        chunks: Sequence[DocumentChunk],
        dense_vectors: Sequence[Sequence[float]],
        sparse_vectors: Sequence[models.SparseVector] | None = None,
        batch_size: int = settings.qdrant_upsert_batch_size,
        wait: bool = True,
    ) -> int:
        self._validate_vector_lengths(chunks, dense_vectors, sparse_vectors)

        total = 0
        for start in range(0, len(chunks), batch_size):
            end = start + batch_size
            batch_points = [
                self._build_point(
                    chunk=chunk,
                    dense_vector=dense_vector,
                    sparse_vector=sparse_vector,
                )
                for chunk, dense_vector, sparse_vector in zip(
                    chunks[start:end],
                    dense_vectors[start:end],
                    self._slice_sparse_vectors(sparse_vectors, start, end),
                )
            ]

            if not batch_points:
                continue

            self.client.upsert(
                collection_name=collection_name,
                points=batch_points,
                wait=wait,
            )
            total += len(batch_points)

        return total

    def upsert_points(
        self,
        collection_name: str,
        points: Sequence[models.PointStruct],
        wait: bool = True,
    ) -> int:
        if not points:
            return 0

        self.client.upsert(
            collection_name=collection_name,
            points=list(points),
            wait=wait,
        )
        return len(points)

    def search_dense(
        self,
        collection_name: str,
        query_vector: Sequence[float],
        top_k: int = 10,
        allowed_role: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[QdrantSearchResult]:
        scored_points = self.client.search(
            collection_name=collection_name,
            query_vector=(self.dense_vector_name, list(query_vector)),
            query_filter=self._build_filter(allowed_role, metadata_filter),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        return [self._to_search_result(point) for point in scored_points]

    def search_hybrid(
        self,
        collection_name: str,
        dense_query_vector: Sequence[float],
        sparse_query_vector: models.SparseVector | None,
        top_k: int = 10,
        allowed_role: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
        prefetch_limit: int | None = None,
    ) -> list[QdrantSearchResult]:
        if sparse_query_vector is None:
            return self.search_dense(
                collection_name=collection_name,
                query_vector=dense_query_vector,
                top_k=top_k,
                allowed_role=allowed_role,
                metadata_filter=metadata_filter,
            )

        query_filter = self._build_filter(allowed_role, metadata_filter)
        prefetch_limit = prefetch_limit or max(top_k * 4, top_k)

        if hasattr(self.client, "query_points") and hasattr(models, "FusionQuery"):
            try:
                response = self.client.query_points(
                    collection_name=collection_name,
                    prefetch=[
                        models.Prefetch(
                            query=list(dense_query_vector),
                            using=self.dense_vector_name,
                            filter=query_filter,
                            limit=prefetch_limit,
                        ),
                        models.Prefetch(
                            query=sparse_query_vector,
                            using=self.sparse_vector_name,
                            filter=query_filter,
                            limit=prefetch_limit,
                        ),
                    ],
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    query_filter=query_filter,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=False,
                )
                return [
                    self._to_search_result(point)
                    for point in getattr(response, "points", response)
                ]
            except (AttributeError, TypeError, ValueError):
                pass

        return self._search_hybrid_fallback(
            collection_name=collection_name,
            dense_query_vector=dense_query_vector,
            sparse_query_vector=sparse_query_vector,
            query_filter=query_filter,
            top_k=top_k,
            prefetch_limit=prefetch_limit,
        )

    def delete_by_document_id(
        self,
        collection_name: str,
        document_id: str,
        wait: bool = True,
    ) -> None:
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=wait,
        )

    def _search_hybrid_fallback(
        self,
        collection_name: str,
        dense_query_vector: Sequence[float],
        sparse_query_vector: models.SparseVector,
        query_filter: models.Filter | None,
        top_k: int,
        prefetch_limit: int,
    ) -> list[QdrantSearchResult]:
        dense_points = self.client.search(
            collection_name=collection_name,
            query_vector=(self.dense_vector_name, list(dense_query_vector)),
            query_filter=query_filter,
            limit=prefetch_limit,
            with_payload=True,
            with_vectors=False,
        )

        if not hasattr(models, "NamedSparseVector"):
            return [self._to_search_result(point) for point in dense_points[:top_k]]

        sparse_points = self.client.search(
            collection_name=collection_name,
            query_vector=models.NamedSparseVector(
                name=self.sparse_vector_name,
                vector=sparse_query_vector,
            ),
            query_filter=query_filter,
            limit=prefetch_limit,
            with_payload=True,
            with_vectors=False,
        )

        return self._rrf_merge(dense_points, sparse_points, top_k)

    def _build_point(
        self,
        chunk: DocumentChunk,
        dense_vector: Sequence[float],
        sparse_vector: models.SparseVector | None,
    ) -> models.PointStruct:
        vector: dict[str, Any] = {
            self.dense_vector_name: list(dense_vector),
        }
        if sparse_vector is not None:
            vector[self.sparse_vector_name] = sparse_vector

        return models.PointStruct(
            id=self._point_id(chunk.chunk_id),
            vector=vector,
            payload={
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                **chunk.metadata,
            },
        )

    def _build_filter(
        self,
        allowed_role: str | None,
        metadata_filter: dict[str, Any] | None,
    ) -> models.Filter | None:
        conditions: list[models.FieldCondition] = []

        if allowed_role:
            conditions.append(
                models.FieldCondition(
                    key="allowed_roles",
                    match=models.MatchValue(value=allowed_role),
                )
            )

        for key, value in (metadata_filter or {}).items():
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchAny(any=list(value)),
                    )
                )
            else:
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    )
                )

        if not conditions:
            return None

        return models.Filter(must=conditions)

    def _rrf_merge(
        self,
        dense_points: Sequence[Any],
        sparse_points: Sequence[Any],
        top_k: int,
        rrf_k: int = 60,
    ) -> list[QdrantSearchResult]:
        merged: dict[str, tuple[float, Any]] = {}

        for points in (dense_points, sparse_points):
            for rank, point in enumerate(points, start=1):
                point_id = str(point.id)
                score = 1.0 / (rrf_k + rank)
                current_score, _ = merged.get(point_id, (0.0, point))
                merged[point_id] = (current_score + score, point)

        ranked = sorted(merged.values(), key=lambda item: item[0], reverse=True)
        return [
            self._to_search_result(point, score=score)
            for score, point in ranked[:top_k]
        ]

    @staticmethod
    def _point_id(chunk_id: str) -> str:
        return str(uuid5(NAMESPACE_URL, chunk_id))

    @staticmethod
    def _to_search_result(
        point: Any,
        score: float | None = None,
    ) -> QdrantSearchResult:
        payload = dict(point.payload or {})
        content = str(payload.pop("content", ""))
        return QdrantSearchResult(
            point_id=str(point.id),
            score=float(point.score if score is None else score),
            content=content,
            metadata=payload,
            payload=dict(point.payload or {}),
        )

    @staticmethod
    def _slice_sparse_vectors(
        sparse_vectors: Sequence[models.SparseVector] | None,
        start: int,
        end: int,
    ) -> Sequence[models.SparseVector | None]:
        if sparse_vectors is None:
            return [None] * (end - start)
        return sparse_vectors[start:end]

    @staticmethod
    def _validate_vector_lengths(
        chunks: Sequence[DocumentChunk],
        dense_vectors: Sequence[Sequence[float]],
        sparse_vectors: Sequence[models.SparseVector] | None,
    ) -> None:
        if len(chunks) != len(dense_vectors):
            raise ValueError(
                "chunks and dense_vectors must have the same length: "
                f"{len(chunks)} != {len(dense_vectors)}"
            )

        if sparse_vectors is not None and len(chunks) != len(sparse_vectors):
            raise ValueError(
                "chunks and sparse_vectors must have the same length: "
                f"{len(chunks)} != {len(sparse_vectors)}"
            )
