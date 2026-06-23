import cv2
import numpy as np


# 5 landmark chuẩn của ArcFace — tọa độ trên ảnh 112x112
# Thứ tự: left_eye, right_eye, nose, left_mouth, right_mouth
ARCFACE_DST = np.array([
    [38.2946, 51.6963],
    [73.5318, 51.5014],
    [56.0252, 71.7366],
    [41.5493, 92.3655],
    [70.7299, 92.2041],
], dtype=np.float32)


class FaceAligner:

    def __init__(self, output_size: tuple[int, int] = (112, 112)):
        self.output_size = output_size

    def align(self, img: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
        # Scale dst landmarks theo output_size nếu khác 112x112
        dst = ARCFACE_DST.copy()
        if self.output_size != (112, 112):
            dst[:, 0] *= self.output_size[0] / 112
            dst[:, 1] *= self.output_size[1] / 112

        # Tính affine matrix từ 5 điểm landmark
        transform = cv2.estimateAffinePartial2D(
            landmarks, dst,
            method=cv2.LMEDS,
        )[0]

        # Warp ảnh gốc về chuẩn
        aligned = cv2.warpAffine(
            img,
            transform,
            self.output_size,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT,
        )
        return aligned

    def align_from_detection(self, img: np.ndarray, detection) -> np.ndarray:
        return self.align(img, detection.landmarks)

from insightface.utils import face_align