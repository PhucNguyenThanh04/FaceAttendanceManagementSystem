import asyncio
import logging
import numpy as np
from typing import Optional

from app.core.pipeline.pipe_processor import PipelineProcessor
from app.core.configs.settings import settings
from app.utils.setup_logger import setup_logger
from app.api.v1.features.register import schemas as schemas_register
from app.core.vector_db import schemas as schemas_vector
from app.core.vector_db.qdrant_repo import Vectordb

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.92


class RegisterService:

    def __init__(self, pipeline: PipelineProcessor, vectordb: Vectordb):
        self.pipeline = pipeline
        self.vectordb = vectordb
        self._pending: dict[str, list[np.ndarray]] = {}
        self._lock = asyncio.Lock()

    # ── Upload từng ảnh ───────────────────────────────────────────────────────

    async def add_photo(
        self,
        session_id: str,
        image: np.ndarray,
    ) -> schemas_register.AddPhotoResponse:
        result = await asyncio.to_thread(self.pipeline.analyze_frame, image)

        if not result["valid"]:
            return schemas_register.AddPhotoResponse(
                accepted=False,
                reason=result["reason"],
            )

        new_emb = result["embedding"]   # np.ndarray (512,) đã normalize

        async with self._lock:
            existing = self._pending.get(session_id, [])

            # Diversity check — embedding đã normalize → dot = cosine similarity
            for old_emb in existing:
                if float(np.dot(new_emb, old_emb)) > SIMILARITY_THRESHOLD:
                    return schemas_register.AddPhotoResponse(
                        accepted=False,
                        reason="Ảnh quá giống ảnh đã chụp — hãy thay đổi góc mặt.",
                        count=len(existing),
                    )

            existing.append(new_emb)
            self._pending[session_id] = existing
            count = len(existing)   # lưu trong lock → chính xác

        return schemas_register.AddPhotoResponse(
            accepted=True,
            count=count,
            quality_score=result.get("quality_score"),
        )

    # ── Commit ────────────────────────────────────────────────────────────────

    async def commit(
        self,
        session_id: str,
        payload: schemas_vector.PayloadCreateRequest,
    ) -> schemas_register.CommitResponse:
        """
        Lấy embedding từ RAM → upsert vào Qdrant kèm payload → xóa khỏi RAM.

        payload gồm: staff_id, face_profile_id, username, status,
                     embedding_version, created_at
        — do API server tạo và gửi kèm lệnh commit.
        """
        async with self._lock:
            embeddings = self._pending.pop(session_id, None)

        if not embeddings:
            raise ValueError(f"Session '{session_id}' không tồn tại hoặc đã được commit.")

        vector_ids = await self.vectordb.add_vectors_batch(
            vectors=embeddings,
            payload=payload,
        )

        logger.info(
            "Commit thành công | staff_id=%s | face_profile_id=%s | vectors=%d",
            payload.staff_id, payload.face_profile_id, len(vector_ids),
        )
        return schemas_register.CommitResponse(
            success=True,
            staff_id=payload.staff_id,
            face_profile_id=payload.face_profile_id,
            vectors_stored=len(vector_ids),
        )

    # ── Re-enroll ─────────────────────────────────────────────────────────────

    async def re_enroll(
        self,
        session_id: str,
        payload: schemas_vector.PayloadCreateRequest,
    ) -> schemas_register.CommitResponse:
        """
        Xóa vector cũ theo face_profile_id → commit embedding mới.
        Dùng khi admin chụp lại ảnh cho 1 profile cụ thể.
        """
        deleted = await self.vectordb.delete_by_face_profile_id(payload.face_profile_id)
        logger.info(
            "Re-enroll: đã xóa %d vector cũ | face_profile_id=%s",
            deleted, payload.face_profile_id,
        )
        return await self.commit(session_id, payload)

    # ── Hủy session ───────────────────────────────────────────────────────────

    async def cancel(self, session_id: str) -> None:
        """Hủy session — xóa embedding đang pending, không commit."""
        async with self._lock:
            removed = self._pending.pop(session_id, None)
        count = len(removed) if removed else 0
        logger.info("Huỷ session '%s' | %d embeddings bị xóa", session_id, count)

    # ── Xóa nhân viên ─────────────────────────────────────────────────────────

    async def delete_person(self, staff_id: str) -> int:
        """Xóa toàn bộ vector của 1 nhân viên khỏi Qdrant."""
        deleted = await self.vectordb.delete_by_staff_id(staff_id)
        logger.info("Đã xóa %d vector | staff_id=%s", deleted, staff_id)
        return deleted

    # ── Kiểm tra enroll ───────────────────────────────────────────────────────

    async def count_vectors(self, staff_id: str) -> int:
        """Kiểm tra số vector hiện có của 1 nhân viên."""
        return await self.vectordb.count_by_staff_id(staff_id)