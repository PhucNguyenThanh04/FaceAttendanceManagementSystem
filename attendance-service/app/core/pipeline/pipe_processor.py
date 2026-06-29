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
    BLUR_MIN = 0.0   # Laplacian variance
    BRIGHTNESS_MIN = 50.0
    BRIGHTNESS_MAX = 230.0
    YAW_MAX = 65.0
    QUALITY_SCORE_MIN = 0.1


def _fail(stage: str, reason: str, bbox: list[int] | None = None) -> dict:
    result = {"valid": False, "stage": stage, "reason": reason}
    if bbox is not None:
        result["bbox"] = bbox
    return result

def _ok(embedding: np.ndarray, quality_score: float, bbox: list[int]) -> dict:
    return {
        "valid": True,
        "embedding": embedding,
        "quality_score": quality_score,
        "bbox": bbox,
    }

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

    def try_get_embedding(self, image: np.ndarray) -> tuple[bool, Optional[np.ndarray]]:
        acquired, embedding, _ = self.try_get_embedding_with_bbox(image)
        return acquired, embedding

    def try_run_pipeline(self, image: np.ndarray) -> tuple[bool, dict | None]:
        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            return False, None

        try:
            return True, self._run_pipeline(image)
        finally:
            self._lock.release()

    def try_get_embedding_with_bbox(
        self,
        image: np.ndarray,
    ) -> tuple[bool, Optional[np.ndarray], list[int] | None]:
        acquired, result = self.try_run_pipeline(image)
        if not acquired or result is None:
            return False, None, None

        if result["valid"]:
            return True, result["embedding"], result.get("bbox")
        logger.debug("[attendance] skip frame: %s", result["reason"])
        return True, None, result.get("bbox")

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
        if image is None or not isinstance(image, np.ndarray) or image.size == 0 or image.ndim < 2:
            return _fail("input", "Frame camera không hợp lệ.")

        image_h, image_w = image.shape[:2]

        # ── Step 1: Detect ───────────────────────────────────────────────
        detections = self.detector.detect(image)

        if len(detections) == 0:
            return _fail("detect", "Không phát hiện khuôn mặt nào.")
        if len(detections) > 1:
            return _fail("detect", f"Phát hiện {len(detections)} khuôn mặt — chỉ chấp nhận 1.")

        det = detections[0]
        raw_bbox = list(map(int, det["bbox"]))
        kps = det.get("kps")
        if kps is None:
            return _fail("detect", "Detector không trả về landmark khuôn mặt.", raw_bbox)

        landmarks = np.array(kps, dtype=np.float32)
        if landmarks.shape != (5, 2) or not np.isfinite(landmarks).all():
            return _fail("detect", "Landmark khuôn mặt không hợp lệ.", raw_bbox)

        det_score = float(det["score"])
        raw_x1, raw_y1, raw_x2, raw_y2 = raw_bbox
        x1 = max(0, min(raw_x1, image_w))
        y1 = max(0, min(raw_y1, image_h))
        x2 = max(0, min(raw_x2, image_w))
        y2 = max(0, min(raw_y2, image_h))
        bbox = [x1, y1, x2, y2]

        if x2 <= x1 or y2 <= y1:
            return _fail("quality", "Vùng khuôn mặt nằm ngoài khung hình camera.", raw_bbox)
        if bbox != raw_bbox:
            logger.debug(
                "Face bbox clamped to frame bounds: raw=%s clamped=%s frame=%sx%s",
                raw_bbox,
                bbox,
                image_w,
                image_h,
            )

        face_w, face_h = x2 - x1, y2 - y1

        # ── Step 2: Quality check ────────────────────────────────────────
        if face_w < self.thr.FACE_MIN_SIZE or face_h < self.thr.FACE_MIN_SIZE:
            return _fail("quality", f"Khuôn mặt quá nhỏ ({face_w:.0f}×{face_h:.0f}px) — đứng gần camera hơn.", bbox)

        if det_score < self.thr.DET_SCORE_MIN:
            return _fail("quality", f"Độ tin cậy phát hiện quá thấp ({det_score:.2f}).", bbox)

        face_crop = image[y1:y2, x1:x2]
        if face_crop.size == 0:
            return _fail("quality", "Vùng khuôn mặt rỗng sau khi cắt ảnh.", bbox)

        blur_score = calculate_blur_score(face_crop)
        brightness = calculate_brightness(face_crop)
        pose = estimate_head_pose(landmarks, bbox)
        occlusion = check_occlusion(face_crop, landmarks)
        yaw = pose["yaw"]

        if blur_score < self.thr.BLUR_MIN:
            return _fail("quality", f"Ảnh bị mờ (blur={blur_score:.1f}) — giữ yên camera.", bbox)
        if brightness < self.thr.BRIGHTNESS_MIN:
            return _fail("quality", f"Ảnh quá tối (brightness={brightness:.1f}) — cần thêm ánh sáng.", bbox)
        if brightness > self.thr.BRIGHTNESS_MAX:
            return _fail("quality", f"Ảnh quá sáng (brightness={brightness:.1f}) — giảm ánh sáng.", bbox)
        # Chỉ chặn khi quay trái/phải quá lớn, không check pitch/roll
        yaw_abs = abs(yaw)
        logger.debug("Pose yaw=%.2f (abs=%.2f, max=%.2f)", yaw, yaw_abs, self.thr.YAW_MAX)
        if yaw_abs > self.thr.YAW_MAX:
            return _fail("quality", f"Mặt quay ngang quá nhiều (yaw={yaw:.1f}°), vui lòng nhìn thẳng camera hơn.", bbox)
        if occlusion["severe"]:
            return _fail("quality", "Khuôn mặt bị che khuất.", bbox)

        quality_score = calculate_quality_score({
            "det_score":        det_score,
            "blur_score":       blur_score,
            "brightness_score": brightness,
            # chỉ dùng yaw cho pose score; pitch/roll để 0 tránh ảnh hưởng
            "yaw": yaw, "pitch": 0.0, "roll": 0.0,
            "occlusion_score":  occlusion["score"],
        })
        if quality_score < self.thr.QUALITY_SCORE_MIN:
            return _fail("quality", f"Chất lượng ảnh tổng hợp quá thấp ({quality_score:.2f}).", bbox)

        # ── Step 3: Anti-spoofing ────────────────────────────────────────
        spoof_result = self.antispoof_manager.check_anti_spoof(image, bbox)
        is_real = bool(spoof_result.get("is_real", False))
        spoof_conf = float(spoof_result.get("confidence", 0.0))

        if not is_real:
            return _fail("antispoof", f"Phát hiện ảnh giả mạo (confidence={spoof_conf:.2f}).", bbox)

        aligned = norm_crop(image, landmarks)

        # ── Step 5: Embed ────────────────────────────────────────────────
        embedding = self.embedder.get_embedding(aligned)

        return _ok(embedding, quality_score, bbox)
