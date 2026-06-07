import uuid
import numpy as np
from datetime import datetime, timezone
from collections import defaultdict
from typing import List

from qdrant_client import AsyncQdrantClient, models
from app.utils.setup_logger import setup_logger
from app.core.vector_db import schemas as vector_schemas

logger = setup_logger(__name__)


class Vectordb:

    def __init__(
        self,
        _client: AsyncQdrantClient,
        _collection_name: str,
        _dim: int = 512,
    ) -> None:
        self.client = _client
        self.collection_name = _collection_name
        self.dim = _dim

    async def create_collection(self) -> None:
        if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.dim,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Tạo collection '%s' thành công", self.collection_name)
        else:
            logger.info("Collection '%s' đã tồn tại", self.collection_name)

    # ── Write ─────────────────────────────────────────────────────────────────

    async def add_vectors_batch(
        self,
        vectors: list[np.ndarray],
        payload: vector_schemas.PayloadCreateRequest,
    ) -> List[str]:
        created_at = payload.created_at or datetime.now(timezone.utc).isoformat()
        updated_at = payload.updated_at or created_at

        points= []
        vector_ids = []

        for vec in vectors:
            v= self._validate_and_normalize(vec)
            vid = str(uuid.uuid4())
            vector_ids.append(vid)
            points.append(
                models.PointStruct(
                    id=vid,
                    vector=v,
                    payload={
                        "staff_id":          payload.staff_id,
                        "face_profile_id":   payload.face_profile_id,
                        "employee_code":     payload.employee_code,
                        "embedding_version": payload.embedding_version,
                        "is_active":         payload.is_active,
                        "created_at":        created_at,
                        "updated_at":        updated_at,
                    },
                )
            )

        await self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info(
            "Upserted %d vectors | staff_id=%s | face_profile_id=%s",
            len(points), payload.staff_id, payload.face_profile_id,
        )
        return vector_ids

    async def delete_by_staff_id(self, staff_id: str) -> int:
        existing, _ = await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(must=[
                models.FieldCondition(key="staff_id", match=models.MatchValue(value=staff_id))
            ]),
            limit=100,
            with_payload=False,
            with_vectors=False,
        )
        count = len(existing)
        if count == 0:
            logger.warning("Không có vector nào cho staff_id=%s", staff_id)
            return 0

        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[
                    models.FieldCondition(key="staff_id", match=models.MatchValue(value=staff_id))
                ])
            ),
        )
        logger.info("Đã xóa %d vector | staff_id=%s", count, staff_id)
        return count

    async def delete_by_face_profile_id(self, face_profile_id: str) -> int:
        existing, _ = await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(must=[
                models.FieldCondition(key="face_profile_id", match=models.MatchValue(value=face_profile_id))
            ]),
            limit=100,
            with_payload=False,
            with_vectors=False,
        )
        count = len(existing)
        if count == 0:
            logger.warning("Không có vector nào cho face_profile_id=%s", face_profile_id)
            return 0

        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[
                    models.FieldCondition(key="face_profile_id", match=models.MatchValue(value=face_profile_id))
                ])
            ),
        )
        logger.info("Đã xóa %d vector | face_profile_id=%s", count, face_profile_id)
        return count

    async def update_payload_by_staff_id(
        self,
        staff_id: str,
        payload: vector_schemas.PayloadUpdateRequest,
    ) -> int:
        existing, _ = await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(must=[
                models.FieldCondition(key="staff_id", match=models.MatchValue(value=staff_id))
            ]),
            limit=100,
            with_payload=False,
            with_vectors=False,
        )
        count = len(existing)
        if count == 0:
            logger.warning("Không có vector nào cho staff_id=%s", staff_id)
            return 0

        payload_dict = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not payload_dict:
            logger.warning("Không có trường nào để cập nhật")
            return 0
        payload_dict.setdefault("updated_at", datetime.now(timezone.utc).isoformat())

        await self.client.set_payload(
            collection_name=self.collection_name,
            payload=payload_dict,
            points=models.Filter(must=[
                models.FieldCondition(key="staff_id", match=models.MatchValue(value=staff_id))
            ]),
        )
        logger.info("Đã cập nhật %d vector | staff_id=%s", count, staff_id)
        return count

    async def search_vector(
        self,
        vector: np.ndarray,
        top_k: int = 20,
        threshold: float = 0.80,
    ) -> List[vector_schemas.PayloadSearchResponse]:
        v= self._validate_and_normalize(vector)
        res = await self.client.query_points(
            collection_name=self.collection_name,
            query=v,
            limit=top_k,
            score_threshold=threshold,
        )
        return [
            vector_schemas.PayloadSearchResponse(
                staff_id=p.payload["staff_id"],
                face_profile_id=p.payload["face_profile_id"],
                employee_code=p.payload.get("employee_code") or p.payload.get("username") or "",
                embedding_version=p.payload["embedding_version"],
                is_active=p.payload.get("is_active", p.payload.get("status") == "active"),
                created_at=p.payload["created_at"],
                updated_at=p.payload.get("updated_at"),
                score=p.score,
                qdrant_id=str(p.id),
            )
            for p in res.points
        ]

    async def identify_person(
        self,
        vector: np.ndarray,
        top_k: int = 20,
        threshold: float = 0.80,
        final_threshold: float = 0.85,
        min_votes: int = 2,
        gap_threshold: float = 0.04,
    ) -> vector_schemas.PayloadIdentifyResponse:
        candidates = await self.search_vector(vector=vector, top_k=top_k, threshold=threshold)
        candidates = [
            candidate
            for candidate in candidates
            if candidate.is_active
        ]

        if not candidates:
            return vector_schemas.PayloadIdentifyResponse(status="unknown", person=None)

        # Gom nhóm theo staff_id
        person_scores: dict[str, list[float]]= defaultdict(list)
        person_info:   dict[str, vector_schemas.PayloadSearchResponse] = {}

        for c in candidates:
            person_scores[c.staff_id].append(c.score)
            if c.staff_id not in person_info or c.score > person_info[c.staff_id].score:
                person_info[c.staff_id] = c

        # Tính aggregated score
        person_agg: dict[str, float] = {}
        for sid, scores in person_scores.items():
            if len(scores) < min_votes or max(scores) < final_threshold:
                continue
            avg_top3 = sum(sorted(scores, reverse=True)[:3]) / min(3, len(scores))
            person_agg[sid] = 0.6 * max(scores) + 0.4 * avg_top3

        if not person_agg:
            return vector_schemas.PayloadIdentifyResponse(status="unknown", person=None)

        ranked = sorted(person_agg.items(), key=lambda x: x[1], reverse=True)
        top_id, top_score = ranked[0]

        # Kiểm tra ambiguous
        if len(ranked) > 1 and (top_score - ranked[1][1]) < gap_threshold:
            logger.warning("Ambiguous: gap quá nhỏ giữa top 2")
            return vector_schemas.PayloadIdentifyResponse(status="ambiguous", person=None)

        winner = person_info[top_id]
        logger.info(
            "Recognized: employee_code=%s | confidence=%.4f",
            winner.employee_code,
            top_score,
        )

        return vector_schemas.PayloadIdentifyResponse(
            status="recognized",
            person=winner,
            votes=len(person_scores[top_id]),
            total=len(candidates),
            confidence=top_score,
        )

    async def count_by_staff_id(self, staff_id: str) -> int:
        existing, _ = await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(must=[
                models.FieldCondition(key="staff_id", match=models.MatchValue(value=staff_id))
            ]),
            limit=100,
            with_payload=False,
            with_vectors=False,
        )
        return len(existing)

    @staticmethod
    def _validate_and_normalize(embedding: np.ndarray) -> List[float]:
        embedding = np.array(embedding, dtype=np.float32)
        if embedding.shape[0] != 512:
            raise ValueError("Embedding phải có 512 chiều")
        norm = np.linalg.norm(embedding)
        if norm < 1e-6:
            raise ValueError("Embedding không hợp lệ (norm quá nhỏ)")
        return (embedding / norm).tolist()
