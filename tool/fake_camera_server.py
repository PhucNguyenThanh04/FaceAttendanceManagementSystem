import cv2
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
# logger = setup_logger(__name__)


class MJPEGHandler(BaseHTTPRequestHandler):
    video_path = None
    _lock = threading.Lock()
    _frame = None

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path != "/stream":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type",
                         "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()

        try:
            while True:
                with MJPEGHandler._lock:
                    frame = MJPEGHandler._frame

                if frame is None:
                    time.sleep(0.01)
                    continue

                _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                jpg_bytes = jpg.tobytes()

                self.wfile.write(
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpg_bytes)).encode() + b"\r\n"
                    b"\r\n" + jpg_bytes + b"\r\n"
                )
        except (BrokenPipeError, ConnectionResetError):
            pass

def _center_crop_square(frame):
    h, w = frame.shape[:2]
    size = min(w, h)

    x1 = (w - size) // 2
    y1 = (h - size) // 2

    return frame[y1:y1 + size, x1:x1 + size]


def _capture_loop(video_path: str, fps: float):
    delay = 1.0 / fps

    while True:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)

        if not cap.isOpened():
            raise FileNotFoundError(f"khong mo duoc video: {video_path}")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame = _center_crop_square(frame)
            frame = cv2.resize(frame, (640, 640), interpolation=cv2.INTER_AREA)

            with MJPEGHandler._lock:
                MJPEGHandler._frame = frame

            time.sleep(delay)

        cap.release()



def start_server(video_path: str, host: str ,
                 port: int , fps: float = 2.0):

    MJPEGHandler.video_path = video_path

    t = threading.Thread(
        target=_capture_loop,
        args=(video_path, fps),
        daemon=True,
    )
    t.start()
    print("load video")
    while MJPEGHandler._frame is None:
        time.sleep(0.05)

    server = HTTPServer((host, port), MJPEGHandler)
    print(f"Server started at http://{host}:{port}/stream")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("dung server")
        server.shutdown()


if __name__ == '__main__':
    import sys
    import os
    from dotenv import load_dotenv
    load_dotenv()
    path = int(sys.argv[1]) if len(sys.argv) > 1 else "0"
    start_server(path, host="0.0.0.0", port=8080, fps=25)


