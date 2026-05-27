import threading
import numpy as np
from typing import Optional

from insightface.utils.face_align import norm_crop
from app.core.utils_ml_pipeline.check_quality_face import (
    calculate_blur_score,
    calculate_brightness,
    estimate_head_pose,
    check_occlusion,
    calculate_quality_score,
)
from app.core.ml.Detector import Detector
from app.core.ml.Embedder import Embedder
from app.core.ml.AntiSpoofting import AntiSpoofModelManager
from app.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


# ── Threshold config ──────────────────────────────────────────────────────────

class QualityThreshold:
    FACE_MIN_SIZE = 60     # pixel
    DET_SCORE_MIN = 0.65
    BLUR_MIN = 30.0   # Laplacian variance
    BRIGHTNESS_MIN = 50.0
    BRIGHTNESS_MAX = 230.0
    YAW_MAX = 45.0
    QUALITY_SCORE_MIN = 0.5


def _fail(stage: str, reason: str) -> dict:
    return {"valid": False, "stage": stage, "reason": reason}

def _ok(embedding: np.ndarray, quality_score: float) -> dict:
    return {"valid": True, "embedding": embedding, "quality_score": quality_score}

class PipelineProcessor:

    def __init__(
        self,
        weight_detector: str,
        weight_embedder: str,
        model_dir_antispoof: str,
        device: int = 0,
    ) -> None:
        self.detector = Detector(model_weight=weight_detector, device=device)
        self.embedder = Embedder(model_weight=weight_embedder, device=device)
        self.antispoof_manager = AntiSpoofModelManager(
            model_dir=model_dir_antispoof,
            device_id=device,
            threshold=0.6,
        )
        self.thr   = QualityThreshold()
        self._lock = threading.Lock()
        logger.info("PipelineProcessor khởi tạo thành công")

    def analyze_frame(self, image: np.ndarray) -> dict:
        with self._lock:
            return self._run_pipeline(image)

    def get_embedding(self, image: np.ndarray) -> Optional[np.ndarray]:
        with self._lock:
            result = self._run_pipeline(image)
        if result["valid"]:
            return result["embedding"]
        logger.debug("[attendance] skip frame: %s", result["reason"])
        return None

    def warmup(self, iterations: int = 2) -> None:

        if iterations < 1:
            iterations = 1

        dummy_frame = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        dummy_face = np.random.randint(0, 256, (112, 112, 3), dtype=np.uint8)
        dummy_bbox = [64, 64, 192, 192]

        with self._lock:
            for idx in range(iterations):
                try:
                    self.detector.detect(dummy_frame)
                except Exception as e:
                    logger.warning("Warmup detector failed at iter %d: %s", idx + 1, e)

                try:
                    self.antispoof_manager.check_anti_spoof(dummy_frame, dummy_bbox)
                except Exception as e:
                    logger.warning("Warmup antispoof failed at iter %d: %s", idx + 1, e)

                try:
                    self.embedder.get_embedding(dummy_face)
                except Exception as e:
                    logger.warning("Warmup embedder failed at iter %d: %s", idx + 1, e)

        logger.info("Pipeline warmup completed (%d iterations)", iterations)

    def _run_pipeline(self, image: np.ndarray) -> dict:

        # ── Step 1: Detect ───────────────────────────────────────────────
        detections = self.detector.detect(image)

        if len(detections) == 0:
            return _fail("detect", "Không phát hiện khuôn mặt nào.")
        if len(detections) > 1:
            return _fail("detect", f"Phát hiện {len(detections)} khuôn mặt — chỉ chấp nhận 1.")

        det = detections[0]
        bbox = det["bbox"]
        landmarks = np.array(det["kps"], dtype=np.float32)
        det_score = float(det["score"])
        x1, y1, x2, y2 = bbox
        face_w, face_h = x2 - x1, y2 - y1

        # ── Step 2: Quality check ────────────────────────────────────────
        if face_w < self.thr.FACE_MIN_SIZE or face_h < self.thr.FACE_MIN_SIZE:
            return _fail("quality", f"Khuôn mặt quá nhỏ ({face_w:.0f}×{face_h:.0f}px) — đứng gần camera hơn.")

        if det_score < self.thr.DET_SCORE_MIN:
            return _fail("quality", f"Độ tin cậy phát hiện quá thấp ({det_score:.2f}).")

        face_crop = image[int(y1):int(y2), int(x1):int(x2)]
        blur_score = calculate_blur_score(face_crop)
        brightness = calculate_brightness(face_crop)
        pose = estimate_head_pose(landmarks, bbox)
        occlusion = check_occlusion(face_crop, landmarks)
        yaw = pose["yaw"]

        if blur_score < self.thr.BLUR_MIN:
            return _fail("quality", f"Ảnh bị mờ (blur={blur_score:.1f}) — giữ yên camera.")
        if brightness < self.thr.BRIGHTNESS_MIN:
            return _fail("quality", f"Ảnh quá tối (brightness={brightness:.1f}) — cần thêm ánh sáng.")
        if brightness > self.thr.BRIGHTNESS_MAX:
            return _fail("quality", f"Ảnh quá sáng (brightness={brightness:.1f}) — giảm ánh sáng.")
        # Chỉ chặn khi quay trái/phải quá lớn, không check pitch/roll
        yaw_abs = abs(yaw)
        logger.debug("Pose yaw=%.2f (abs=%.2f, max=%.2f)", yaw, yaw_abs, self.thr.YAW_MAX)
        if yaw_abs > self.thr.YAW_MAX:
            return _fail("quality", f"Mặt quay ngang quá nhiều (yaw={yaw:.1f}°), vui lòng nhìn thẳng camera hơn.")
        if occlusion["severe"]:
            return _fail("quality", "Khuôn mặt bị che khuất.")

        quality_score = calculate_quality_score({
            "det_score":        det_score,
            "blur_score":       blur_score,
            "brightness_score": brightness,
            # chỉ dùng yaw cho pose score; pitch/roll để 0 tránh ảnh hưởng
            "yaw": yaw, "pitch": 0.0, "roll": 0.0,
            "occlusion_score":  occlusion["score"],
        })
        if quality_score < self.thr.QUALITY_SCORE_MIN:
            return _fail("quality", f"Chất lượng ảnh tổng hợp quá thấp ({quality_score:.2f}).")

        # ── Step 3: Anti-spoofing ────────────────────────────────────────
        spoof_result = self.antispoof_manager.check_anti_spoof(image, bbox)
        is_real = bool(spoof_result.get("is_real", False))
        spoof_conf = float(spoof_result.get("confidence", 0.0))

        if not is_real:
            return _fail("antispoof", f"Phát hiện ảnh giả mạo (confidence={spoof_conf:.2f}).")

        aligned = norm_crop(image, landmarks)

        # ── Step 5: Embed ────────────────────────────────────────────────
        embedding = self.embedder.get_embedding(aligned)

        return _ok(embedding, quality_score)
