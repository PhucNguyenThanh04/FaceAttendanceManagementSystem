import threading
import numpy as np
from typing import Optional

from insightface.utils.face_align import norm_crop

from app.core.ml.Detector import Detector
from app.core.ml.Embedder import Embedder
from app.core.ml.AntiSpoofting import AntiSpoofModelManager
from app.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class PipelineProcessor:
    """
    Pipeline ML dùng chung toàn app.
    Thread-safe: dùng threading.Lock() bảo vệ model inference.

    Thứ tự xử lý:
        detect() → antispoof() → norm_crop() → embed()
    """

    def __init__(
        self,
        weight_detector: str,
        weight_embedder: str,
        model_dir_antispoof: str,
        device: int = 0,
    ) -> None:
        self.detector         = Detector(model_weight=weight_detector, device=device)
        self.embedder         = Embedder(model_weight=weight_embedder, device=device)
        self.antispoof_manager = AntiSpoofModelManager(
            model_dir=model_dir_antispoof,
            device_id=device,
            threshold=0.6,
        )
        self._lock = threading.Lock()
        logger.info("FaceProcessor initialized")

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────
    def _detect_and_align(self, image: np.ndarray) -> np.ndarray:
        """
        Core pipeline (KHÔNG thread-safe — gọi bên trong _lock).

        Raises ValueError với mô tả rõ ràng cho mọi trường hợp thất bại.
        """
        detections = self.detector.detect(image)

        if len(detections) == 0:
            raise ValueError("Không phát hiện khuôn mặt nào trong ảnh.")

        if len(detections) > 1:
            raise ValueError(
                f"Phát hiện {len(detections)} khuôn mặt — chỉ chấp nhận 1 mặt."
            )

        det = detections[0]

        # ── Anti-Spoofing ────────────────────────────────────────────────
        spoof_result = self.antispoof_manager.check_anti_spoof(image, det["bbox"])
        if not spoof_result.get("is_real", False):
            raise ValueError(
                f"Phát hiện ảnh giả mạo (spoof) — confidence: "
                f"{spoof_result.get('confidence', 0):.2f}."
            )

        # ── Confidence score ─────────────────────────────────────────────
        if det["score"] < 0.7:
            raise ValueError(
                f"Confidence phát hiện khuôn mặt quá thấp: {det['score']:.2f}."
            )

        # ── Face size ───────────────────────────────────────────────────
        x1, y1, x2, y2 = det["bbox"]
        face_w = x2 - x1
        face_h = y2 - y1
        if face_w < 60 or face_h < 60:
            raise ValueError(
                f"Khuôn mặt quá nhỏ ({face_w:.0f}×{face_h:.0f}px) — "
                f"hãy đứng gần camera hơn."
            )

        # ── Alignment ──────────────────────────────────────────────────
        landmarks = np.array(det["kps"], dtype=np.float32)
        aligned = norm_crop(image, landmarks)  # → (112, 112, 3)

        return aligned
    def face_detection(self, image: np.ndarray) -> np.ndarray:
        """
        Detect → AntiSpoof → Align.

        Returns:
            aligned face (112×112×3, BGR)

        Raises:
            ValueError: khi ảnh không hợp lệ (không có mặt, spoof,
                        confidence thấp, mặt quá nhỏ, nhiều mặt).
        """
        with self._lock:
            return self._detect_and_align(image)

    def detect_align_embed(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect → AntiSpoof → Align → Embed.
        Dùng cho attendance worker (nhận dạng real-time).

        Returns:
            embedding vector (512,) đã normalize, hoặc None nếu không hợp lệ.
        """
        try:
            result = self.analyze_frame(image)
            if result["valid"]:
                return result["embedding"]
            logger.debug(f"detect_align_embed bỏ qua frame: {result['reason']}")
            return None
        except ValueError as e:
            logger.debug(f"detect_align_embed bỏ qua frame: {e}")
            return None

    def analyze_frame(self, image: np.ndarray) -> dict:
        """
        Chạy toàn bộ pipeline và trả metadata chi tiết để debug/overlay UI.
        """
        with self._lock:
            detections = self.detector.detect(image)

            if len(detections) == 0:
                return {
                    "valid": False,
                    "stage": "detect",
                    "reason": "No face detected",
                    "faces": 0,
                }

            if len(detections) > 1:
                return {
                    "valid": False,
                    "stage": "detect",
                    "reason": f"Multiple faces detected ({len(detections)})",
                    "faces": len(detections),
                }

            det = detections[0]
            x1, y1, x2, y2 = det["bbox"]
            face_w = x2 - x1
            face_h = y2 - y1

            spoof_result = self.antispoof_manager.check_anti_spoof(image, det["bbox"])
            is_real = bool(spoof_result.get("is_real", False))
            spoof_conf = float(spoof_result.get("confidence", 0.0))
            spoof_label = int(spoof_result.get("label", -1))

            if not is_real:
                return {
                    "valid": False,
                    "stage": "antispoof",
                    "reason": f"Spoof detected (conf={spoof_conf:.2f}, label={spoof_label})",
                    "faces": 1,
                    "det_score": float(det["score"]),
                    "face_size": (int(face_w), int(face_h)),
                    "is_real": is_real,
                    "spoof_confidence": spoof_conf,
                    "spoof_label": spoof_label,
                }

            if det["score"] < 0.7:
                return {
                    "valid": False,
                    "stage": "detect",
                    "reason": f"Low detection confidence ({det['score']:.2f})",
                    "faces": 1,
                    "det_score": float(det["score"]),
                    "face_size": (int(face_w), int(face_h)),
                    "is_real": is_real,
                    "spoof_confidence": spoof_conf,
                    "spoof_label": spoof_label,
                }

            if face_w < 60 or face_h < 60:
                return {
                    "valid": False,
                    "stage": "face_size",
                    "reason": f"Face too small ({face_w:.0f}x{face_h:.0f})",
                    "faces": 1,
                    "det_score": float(det["score"]),
                    "face_size": (int(face_w), int(face_h)),
                    "is_real": is_real,
                    "spoof_confidence": spoof_conf,
                    "spoof_label": spoof_label,
                }

            landmarks = np.array(det["kps"], dtype=np.float32)
            aligned = norm_crop(image, landmarks)
            embedding = self.embedder.get_embedding(aligned)

            return {
                "valid": True,
                "stage": "ok",
                "reason": "Ready for identification",
                "faces": 1,
                "det_score": float(det["score"]),
                "face_size": (int(face_w), int(face_h)),
                "is_real": is_real,
                "spoof_confidence": spoof_conf,
                "spoof_label": spoof_label,
                "embedding": embedding,
            }




