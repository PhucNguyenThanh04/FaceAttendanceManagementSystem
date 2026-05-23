import insightface
import numpy as np
from typing import List, Dict
from app.utils.setup_logger import setup_logger

logger = setup_logger(__name__)

class Detector:

    def __init__(self,
                 model_weight: str, # path to model weight file
                 device: int = 0,
                 conf_thresh: float = 0.5,
                 img_size: int = 640
                 ) -> None:
        self.model = insightface.model_zoo.get_model(model_weight)
        ctx_id = device if device >= 0 else -1
        self.model.prepare(
            ctx_id=ctx_id,
            input_size=(img_size, img_size),
            det_thresh=conf_thresh,
        )
        logger.info(
            "RetinaFace model loaded (ctx_id=%s)",
            ctx_id,
        )

    def detect(self, frame: np.ndarray, max_num: int = 0) -> List[Dict]:
        bboxes, kpss = self.model.detect(frame, max_num=max_num)

        if bboxes is None or len(bboxes) == 0:
            return []

        if kpss is None:
            logger.warning("No keypoints returned — norm_crop downstream will fail")

        results = []
        for i, bbox in enumerate(bboxes):
            x1, y1, x2, y2 = bbox[:4].astype(int)
            score = float(bbox[4])
            kps = kpss[i].astype(np.float32) if kpss is not None else None

            results.append({
                "bbox": [x1, y1, x2, y2],
                "score": score,
                "kps": kps
            })

        return results


# if __name__ == '__main__':
#     import cv2
#     cap = cv2.VideoCapture(0)
#     detector = Detector(model_weight="weights/det_10g.onnx", device=0)
#
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#         frame = cv2.flip(frame, 1)
#
#         detections = detector.detect(frame)
#
#         for det in detections:
#             x1, y1, x2, y2 = det["bbox"]
#             score = det["score"]
#             kps = det["kps"]
#
#             cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
#             cv2.putText(frame, f"{score:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
#
#             if kps is not None:
#                 for (x, y) in kps:
#                     cv2.circle(frame, (int(x), int(y)), 3, (0, 0, 255), -1)
#
#         cv2.imshow("Frame", frame)
#         if cv2.waitKey(1) & 0xFF == 27:
#             break
#     cap.release()
#     cv2.destroyAllWindows()

