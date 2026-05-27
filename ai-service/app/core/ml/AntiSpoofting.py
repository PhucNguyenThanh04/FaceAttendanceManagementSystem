import os
import sys
from pathlib import Path

import copy
import numpy as np

from app.utils.setup_logger import setup_logger


def _resolve_antispoof_root() -> Path:
    """
    Resolve vendor directory for Silent-Face-Anti-Spoofing.

    Priority:
    1) Env var `ANTI_SPOOF_PROJECT_DIR`
    2) `<backend>/Silent-Face-Anti-Spoofing` (works for local + Docker)
    3) `<cwd>/Silent-Face-Anti-Spoofing` as fallback
    """
    env_dir = os.getenv("ANTI_SPOOF_PROJECT_DIR")
    if env_dir:
        candidate = Path(env_dir).expanduser().resolve()
        if candidate.is_dir():
            return candidate

    backend_dir = Path(__file__).resolve().parents[3]
    candidate = (backend_dir / "Silent-Face-Anti-Spoofing").resolve()
    if candidate.is_dir():
        return candidate

    cwd_candidate = (Path.cwd() / "Silent-Face-Anti-Spoofing").resolve()
    if cwd_candidate.is_dir():
        return cwd_candidate

    raise RuntimeError(
        "Cannot locate 'Silent-Face-Anti-Spoofing'. "
        "Set ANTI_SPOOF_PROJECT_DIR or place the folder under backend/."
    )


ANTI_SPOOF_ROOT = _resolve_antispoof_root()


def _prepend_sys_path(path: Path) -> None:
    """
    Insert path at the beginning of sys.path if missing.
    Compare using resolved absolute paths to avoid duplicates.
    """
    target = str(path.resolve())
    normalized_paths = set()

    for existing in sys.path:
        if not existing:
            continue
        try:
            normalized_paths.add(str(Path(existing).resolve()))
        except OSError:
            # Keep going even if one sys.path entry is malformed/unreadable.
            continue

    if target not in normalized_paths:
        sys.path.insert(0, target)


_prepend_sys_path(ANTI_SPOOF_ROOT)

from src_Antispoofting.anti_spoof_predict import AntiSpoofPredict
from src_Antispoofting.generate_patches import CropImage
from src_Antispoofting.utility import parse_model_name

logger = setup_logger(__name__)


class AntiSpoofModelManager:
    _instance = None

    def __new__(cls, model_dir, device_id=0, threshold=0.8):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init(model_dir, device_id, threshold)
        return cls._instance

    def _init(self, model_dir, device_id, threshold):
        self.model_dir = model_dir
        self.threshold = threshold
        self.device_id = device_id

        self.model_cache = {}
        self.predictor = AntiSpoofPredict(device_id)
        self.cropper = CropImage()

        self.model_list = [
            m for m in os.listdir(model_dir) if m.endswith(".pth")
        ]

        for model_name in self.model_list:
            path = os.path.join(self.model_dir, model_name)
            self.predictor._load_model(path)
            self.model_cache[path] = copy.deepcopy(self.predictor.model)
            logger.info("AntiSpoof preloaded model: %s", model_name)

        # ── Monkey-patch: swap từ cache thay vì đọc disk ──
        cache = self.model_cache
        predictor = self.predictor

        def _cached_load(model_path):
            predictor.model = cache[model_path]

        self.predictor._load_model = _cached_load
        # ──────────────────────────────────────────────────

        logger.info(
            "AntiSpoof cache ready (%s models, cached load enabled).",
            len(self.model_cache),
        )
    def set_model(self, path):
        self.predictor.model = self.model_cache[path]

    def check_anti_spoof(self, frame: np.ndarray, bbox) -> dict:
        if frame is None or bbox is None:
            raise ValueError("Frame hoac bbox dang rong")

        prediction = np.zeros((1, 3))

        x1, y1, x2, y2 = bbox
        bbox_list = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]

        crop_cache = {}

        for model_name in self.model_list:
            path = os.path.join(self.model_dir, model_name)

            h_input, w_input, model_type, scale = parse_model_name(model_name)

            key = (scale, w_input, h_input)

            if key not in crop_cache:
                param = {
                    "org_img": frame,
                    "bbox": bbox_list,
                    "scale": scale,
                    "out_w": w_input,
                    "out_h": h_input,
                    "crop": True,
                }
                crop_cache[key] = self.cropper.crop(**param)

            img = crop_cache[key]

            pred = self.predictor.predict(img, path)

            prediction += pred

        label = int(np.argmax(prediction))
        confidence = float(prediction[0][label] / prediction.sum())

        return {
            "is_real": label == 1 and confidence >= self.threshold,
            "label": label,
            "confidence": confidence,
        }


# if __name__ == '__main__':
#     ap = AntiSpoofModelManager(model_dir="weights/anti_spoof_models")
#
#
#     import cv2
#     cap = cv2.VideoCapture(0)
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#         frame = cv2.flip(frame, 1)
#
#         bbox = [100, 100, 300, 300]
#         result = ap.check_anti_spoof(frame, bbox)
#         print(result)
#
#         cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0,255,0), 2)
#         cv2.imshow("Camera", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break
#





