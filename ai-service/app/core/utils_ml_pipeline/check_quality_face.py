# File: ml_utils.py
import numpy as np
import cv2
from typing import Dict, Optional


def calculate_blur_score(face_crop: np.ndarray) -> float:

    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def calculate_brightness(face_crop: np.ndarray) -> float:

    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


# ──────────────── Head Pose ─────────────────────────
def estimate_head_pose(landmarks: np.ndarray, bbox: Optional[np.ndarray] = None) -> Dict[str, float]:

    points = np.asarray(landmarks, dtype=np.float32).copy()
    left_eye, right_eye, nose, left_mouth, right_mouth = points
    # Roll: góc giữa hai mắt
    dy = right_eye[1] - left_eye[1]
    dx = right_eye[0] - left_eye[0]
    roll = np.degrees(np.arctan2(dy, dx))

    # Bù roll trước khi tính yaw để giảm nhiễu khi đầu nghiêng.
    eye_center = (left_eye + right_eye) / 2.0
    theta = -np.radians(roll)
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    rot = np.array([[cos_t, -sin_t], [sin_t, cos_t]], dtype=np.float32)
    points_rot = ((points - eye_center) @ rot.T) + eye_center
    left_eye_r, right_eye_r, nose_r, left_mouth_r, right_mouth_r = points_rot

    # Yaw: kết hợp nhiều chỉ báo theo trục X để ổn định hơn giữa các kiểu khuôn mặt.
    eps = 1e-6

    def _center_ratio(left_x: float, right_x: float, nose_x: float) -> float:
        width = max(right_x - left_x, eps)
        relative = (nose_x - left_x) / width
        # frontal ~= 0, quay trái/phải -> tiến dần về -1 hoặc +1
        return float(np.clip((relative - 0.5) / 0.5, -1.0, 1.0))

    eye_center_ratio = _center_ratio(left_eye_r[0], right_eye_r[0], nose_r[0])
    mouth_center_ratio = _center_ratio(left_mouth_r[0], right_mouth_r[0], nose_r[0])

    # Đối xứng khoảng cách mũi sang 2 bên để bổ sung độ tin cậy.
    eye_left_gap = max(float(nose_r[0] - left_eye_r[0]), 0.0)
    eye_right_gap = max(float(right_eye_r[0] - nose_r[0]), 0.0)
    eye_sym_ratio = (eye_left_gap - eye_right_gap) / (eye_left_gap + eye_right_gap + eps)

    yaw_ratio = 0.45 * eye_center_ratio + 0.35 * mouth_center_ratio + 0.20 * eye_sym_ratio
    yaw = float(np.clip(yaw_ratio * 75.0, -90.0, 90.0))

    # Pitch: lệch lên/xuống dựa vào mắt-mũi
    if bbox is not None:
        eye_avg_y = (left_eye[1] + right_eye[1]) / 2
        nose_y = nose[1]
        face_height = bbox[3] - bbox[1]
        pitch = (nose_y - eye_avg_y) / face_height * 20  # max 20 deg
    else:
        pitch = 0.0

    return {"yaw": float(yaw), "pitch": float(pitch), "roll": float(roll)}


def check_occlusion(face_crop: np.ndarray, landmarks: np.ndarray) -> Dict[str, float]:

    nose = landmarks[2]
    left_mouth = landmarks[3]
    right_mouth = landmarks[4]

    occluded = False
    # Kiểm tra nan hoặc zero
    if np.any(np.isnan(nose)) or np.any(np.isnan(left_mouth)) or np.any(np.isnan(right_mouth)):
        occluded = True
    if np.any(nose == 0) or np.any(left_mouth == 0) or np.any(right_mouth == 0):
        occluded = True

    return {"severe": occluded, "score": 1.0 if occluded else 0.0}


def calculate_quality_score(metrics: Dict[str, float]) -> float:
    weights = {
        "det_score": 0.25,
        "blur_score": 0.2,
        "brightness_score": 0.2,
        "pose_score": 0.2,
        "occlusion_score": 0.15,
    }

    # Normalize blur (giả sử max 200), brightness 0-255, pose max angles
    blur_norm = min(metrics.get("blur_score", 0)/200, 1.0)
    brightness = metrics.get("brightness_score", 128)
    brightness_norm = min(max((brightness-50)/170, 0), 1.0)

    yaw = abs(metrics.get("yaw", 0))
    pitch = abs(metrics.get("pitch", 0))
    roll = abs(metrics.get("roll", 0))
    pose_norm = 1.0 - min((yaw/30 + pitch/20 + roll/20)/3, 1.0)

    occlusion_norm = 1.0 - metrics.get("occlusion_score", 0)

    score = (
        weights["det_score"] * metrics.get("det_score", 0) +
        weights["blur_score"] * blur_norm +
        weights["brightness_score"] * brightness_norm +
        weights["pose_score"] * pose_norm +
        weights["occlusion_score"] * occlusion_norm
    )
    return float(score)
