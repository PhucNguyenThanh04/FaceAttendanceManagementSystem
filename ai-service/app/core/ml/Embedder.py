
import insightface
import numpy as np
from pathlib import Path
from app.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class Embedder:
    def __init__(
        self,
        model_weight: str | Path,  # path to arcface
        device: int = 0,
    ) -> None:
        self.model = insightface.model_zoo.get_model(str(model_weight))
        ctx_id = device if device >= 0 else -1
        self.model.prepare(ctx_id=ctx_id)
        logger.info(
            "ArcFace model loaded (ctx_id=%s)",
            ctx_id,
        )

    def get_embedding(self, aligned_face: np.ndarray) -> np.ndarray:
        if aligned_face is None or np.asarray(aligned_face).size == 0:
            raise ValueError("aligned_face không hợp lệ (None hoặc rỗng)")

        result = self.embedding_batch(aligned_face)
        return result[0]

    def embedding_batch(self, aligned_faces: np.ndarray) -> list[np.ndarray]:
        if aligned_faces is None:
            logger.warning("aligned_faces is None, trả về list rỗng")
            raise ValueError("aligned_faces rong khong emb duoc")

        batch = np.asarray(aligned_faces)
        if batch.size == 0:
            raise ValueError("aligned_faces rỗng, không thể tạo embedding")

        # Chuẩn hóa về (N, H, W, C)
        if batch.ndim == 3:
            batch = np.expand_dims(batch, axis=0)

        if batch.ndim != 4:
            raise ValueError(
                f"aligned_faces phải có shape (N,H,W,C) hoặc (H,W,C), nhận được {batch.shape}"
            )

        # Gọi model 1 lần duy nhất cho toàn bộ batch (hiệu quả hơn vòng lặp)
        embeddings = np.asarray(self.model.get_feat(list(batch)))

        # Một số backend trả (D,) khi N=1
        if embeddings.ndim == 1:
            embeddings = np.expand_dims(embeddings, axis=0)

        if embeddings.ndim != 2:
            raise ValueError(
                f"Model trả output không hợp lệ, cần (N,D) nhưng nhận được {embeddings.shape}"
            )

        return self._normalize_batch(embeddings)

    @staticmethod
    def _normalize(vec: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vec)
        if norm < 1e-6:
            raise ValueError(
                f"Embedding không hợp lệ: norm ({norm:.2e}) quá nhỏ"
            )
        return vec / norm

    @staticmethod
    def _normalize_batch(vectors: np.ndarray) -> list[np.ndarray]:
        norms = np.linalg.norm(vectors, axis=1)  # (N,)

        invalid = np.where(norms < 1e-6)[0]
        if invalid.size > 0:
            raise ValueError(
                f"Embedding không hợp lệ tại index {invalid.tolist()}: norm quá nhỏ"
            )

        normalized = vectors / norms[:, np.newaxis]  # broadcast (N,D) / (N,1)
        return [normalized[i] for i in range(len(normalized))]
