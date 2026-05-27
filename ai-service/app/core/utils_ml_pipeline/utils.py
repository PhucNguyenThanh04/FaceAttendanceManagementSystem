from fastapi import HTTPException
import cv2
import numpy as np


def decode_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(
            status_code=400,
            detail="Không thể đọc ảnh."
        )
    return img


def _decode_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Không thể đọc ảnh — kiểm tra định dạng file.")
    return img

