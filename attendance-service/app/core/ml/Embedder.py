
import numpy as np
import torch
import onnxruntime as ort
import insightface
from pathlib import Path
from app.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


def _onnx_providers(device: int) -> list[str]:
    logger.info(
        "Torch CUDA status: available=%s device_count=%s current_device=%s",
        torch.cuda.is_available(),
        torch.cuda.device_count(),
        torch.cuda.current_device() if torch.cuda.is_available() else None,
    )
    available = ort.get_available_providers()
    if device >= 0 and "CUDAExecutionProvider" in available:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]

    if device >= 0:
        logger.warning(
            "CUDAExecutionProvider is not available; falling back to CPU. available_providers=%s",
            available,
        )
    return ["CPUExecutionProvider"]


class Embedder:
    def __init__(
        self,
        model_weight: str | Path,  # path to arcface
        device: int = 0,
    ) -> None:
        providers = _onnx_providers(device)
        self.model = insightface.model_zoo.get_model(
            str(model_weight),
            providers=providers,
        )
        ctx_id = device if device >= 0 else -1
        self.model.prepare(ctx_id=ctx_id)
        session = getattr(self.model, "session", None)
        active_providers = session.get_providers() if session is not None else providers
        logger.info(
            "ArcFace model loaded (ctx_id=%s, requested_providers=%s, active_providers=%s)",
            ctx_id,
            providers,
            active_providers,
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
