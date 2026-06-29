from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.core.clients.api_server import ApiServerClient, APIAttendanceEventCreate
from app.core.configs.settings import settings
from app.core.pipeline.pipe_processor import PipelineProcessor
from app.core.utils_ml_pipeline.read_camera import FrameData, MJPEGReader
from app.core.vector_db.qdrant_repo import Vectordb
from app.utils.setup_logger import setup_logger

logger = setup_logger(__name__)

OVERLAY_FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
OVERLAY_FONT_BOLD_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


class AttendancePipeline:
    def __init__(
        self,
        pipline: PipelineProcessor,
        vectordb: Vectordb,
        camera_url: str,
        loop: asyncio.AbstractEventLoop,
        api_client: ApiServerClient,
    ) -> None:
        self.pipeline_processor = pipline
        self.vectordb = vectordb
        self.camera_url = camera_url
        self.loop = loop
        self.api_client = api_client
        self._task: asyncio.Task | None = None
        self._reader: MJPEGReader | None = None
        self._running = False
        self._last_staff_id: str | None = None
        self._consecutive_count = 0
        self._last_recognized_at: dict[str, datetime] = {}
        self._last_cooldown_cleanup_mono = time.monotonic()
        self._cooldown_cleanup_interval_seconds = 300.0
        self._pause_until_mono = 0.0
        self._state_lock = threading.Lock()
        self._latest_result: dict = {
            "status": "waiting",
            "message": "Waiting for camera",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def start(self) -> bool:
        if self.is_running:
            logger.info("Attendance worker already running")
            return False

        self._running = True
        self._task = self.loop.create_task(self.camera_loop())
        self._task.add_done_callback(self._log_task_result)
        logger.info("Attendance worker started")
        return True

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        logger.info("Attendance worker stopped")

    def status(self) -> dict:
        return {
            "running": self.is_running,
            "camera_url": self.camera_url,
            "local_cooldown_size": len(self._last_recognized_at),
            "last_staff_id": self._last_staff_id,
            "consecutive_count": self._consecutive_count,
            "pause_remaining_seconds": round(self._get_pause_remaining_seconds(), 3),
        }

    async def camera_loop(self) -> None:
        delay = self._frame_delay_seconds()
        logger.info(
            "Attendance loop started: camera_url=%s process_fps=%.2f",
            self.camera_url,
            1 / delay,
        )

        self._reader = MJPEGReader(self.camera_url).start()
        try:
            while self._running:
                ok, frame_data = self._reader.latest()
                if not ok or frame_data is None:
                    logger.warning("Attendance camera frame not available")
                    self._set_latest_result(
                        status="waiting",
                        message="Waiting for camera frame",
                    )
                    await asyncio.sleep(1.0)
                    continue

                pause_remaining = self._get_pause_remaining_seconds()
                if pause_remaining > 0:
                    await asyncio.sleep(min(delay, pause_remaining))
                    continue

                await self._process_frame(frame_data)
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Attendance loop crashed")
        finally:
            if self._reader is not None:
                self._reader.stop()
                self._reader = None
            self._running = False
            logger.info("Attendance loop exited")

    async def _process_frame(self, frame_data: FrameData) -> None:
        try:
            acquired, pipeline_result = await asyncio.to_thread(
                self.pipeline_processor.try_run_pipeline,
                frame_data.image,
            )
        except Exception as exc:
            logger.exception(
                "Attendance frame processing failed: frame=%s error=%s",
                frame_data.index,
                exc,
            )
            self._reset_confirmation()
            self._set_latest_result(
                status="error",
                message="Không xử lý được frame camera",
                frame_index=frame_data.index,
            )
            return

        if not acquired:
            logger.info(
                "Attendance frame not recognized: frame=%s reason=ml_pipeline_busy",
                frame_data.index,
            )
            self._set_latest_result(
                status="busy",
                message="Đang xử lý camera",
                frame_index=frame_data.index,
            )
            return

        if pipeline_result is None:
            self._set_latest_result(
                status="scanning",
                message="Đang quét khuôn mặt",
                frame_index=frame_data.index,
            )
            return

        face_box = pipeline_result.get("bbox")
        embedding = pipeline_result.get("embedding") if pipeline_result.get("valid") else None

        if embedding is None:
            status, message = self._pipeline_failure_display(pipeline_result)
            logger.info(
                "Attendance frame not recognized: frame=%s stage=%s reason=%s",
                frame_data.index,
                pipeline_result.get("stage"),
                pipeline_result.get("reason"),
            )
            self._reset_confirmation()
            self._set_latest_result(
                status=status,
                message=message,
                face_box=face_box,
                frame_index=frame_data.index,
            )
            return

        result = await self.vectordb.identify_person(embedding)
        if result.status != "recognized" or result.person is None:
            logger.info(
                "Attendance frame not recognized: frame=%s status=%s confidence=%s",
                frame_data.index,
                result.status,
                result.confidence,
            )
            self._reset_confirmation()
            self._set_latest_result(
                status="not_recognized",
                message="Chưa nhận diện được nhân viên",
                confidence=result.confidence,
                face_box=face_box,
                frame_index=frame_data.index,
            )
            return

        person = result.person
        logger.info(
            "Attendance frame recognized: frame=%s employee_code=%s confidence=%s",
            frame_data.index,
            person.employee_code,
            result.confidence,
        )

        if not self._is_attendance_candidate(person):
            self._reset_confirmation()
            self._set_latest_result(
                status="rejected",
                message=f"{person.employee_code} chưa được phép chấm công",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
                face_box=face_box,
                frame_index=frame_data.index,
            )
            return

        if not self._confirm_same_person(person.staff_id):
            self._set_latest_result(
                status="confirming",
                message=f"Đã nhận diện {person.employee_code}, đang ghi nhận...",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
                face_box=face_box,
                consecutive_count=self._consecutive_count,
                frame_index=frame_data.index,
            )
            return

        if self._in_local_cooldown(person.staff_id):
            self._set_latest_result(
                status="cooldown",
                message=f"{person.employee_code} đã chấm công gần đây",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
                face_box=face_box,
                consecutive_count=self._consecutive_count,
                frame_index=frame_data.index,
            )
            return

        self._set_latest_result(
            status="recording",
            message=f"Đã nhận diện {person.employee_code}, đang ghi nhận...",
            staff_id=person.staff_id,
            employee_code=person.employee_code,
            confidence=result.confidence,
            face_box=face_box,
            consecutive_count=self._consecutive_count,
            frame_index=frame_data.index,
        )
        attendance_response = await self._record_attendance_event(
            person=person,
            confidence=result.confidence,
            frame_index=frame_data.index,
        )

        self._mark_local_cooldown(person.staff_id)
        self._set_pause_after_recognized()

        if attendance_response is None:
            self._set_latest_result(
                status="record_failed",
                message=f"{person.employee_code}: lỗi kết nối API chấm công",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
                face_box=face_box,
                consecutive_count=self._consecutive_count,
                frame_index=frame_data.index,
            )
            return

        if attendance_response.accepted:
            action_label = self._attendance_action_label(attendance_response.event_type)
            self._set_latest_result(
                status="recorded",
                message=f"{person.employee_code} {action_label} thành công",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
                face_box=face_box,
                consecutive_count=self._consecutive_count,
                frame_index=frame_data.index,
                event_id=str(attendance_response.event_id) if attendance_response.event_id else None,
                record_id=str(attendance_response.record_id) if attendance_response.record_id else None,
                event_type=attendance_response.event_type,
            )
        elif attendance_response.reason == "DUPLICATE_ATTENDANCE":
            self._set_latest_result(
                status="cooldown",
                message=f"{person.employee_code} đã chấm công gần đây",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
                face_box=face_box,
                consecutive_count=self._consecutive_count,
                frame_index=frame_data.index,
                cooldown_ttl_seconds=attendance_response.cooldown_ttl_seconds,
            )
        elif attendance_response.reason == "ATTENDANCE_ALREADY_COMPLETED":
            self._set_latest_result(
                status="completed",
                message=f"{person.employee_code} đã hoàn tất chấm công hôm nay",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
                face_box=face_box,
                consecutive_count=self._consecutive_count,
                frame_index=frame_data.index,
            )
        else:
            failure_message = self._attendance_rejection_message(
                person.employee_code,
                attendance_response.reason,
            )
            self._set_latest_result(
                status="record_failed",
                message=failure_message,
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
                face_box=face_box,
                consecutive_count=self._consecutive_count,
                frame_index=frame_data.index,
                reason=attendance_response.reason,
            )

        logger.info(
            "Attendance processed: staff_id=%s employee_code=%s confidence=%s frame=%s accepted=%s reason=%s",
            person.staff_id,
            person.employee_code,
            result.confidence,
            frame_data.index,
            attendance_response.accepted,
            attendance_response.reason,
        )

    @staticmethod
    def _is_attendance_candidate(person) -> bool:
        return person.is_active

    async def _record_attendance_event(
        self,
        *,
        person,
        confidence: float | None,
        frame_index: int,
    ):
        recognized_at = datetime.now(timezone.utc)
        payload = APIAttendanceEventCreate(
            employee_id=person.staff_id,
            event_time=recognized_at,
            confidence_score=confidence,
            anti_spoof_score=None,
            image_url=None,
            raw_result={
                "employee_code": person.employee_code,
                "face_profile_id": person.face_profile_id,
                "qdrant_id": person.qdrant_id,
                "frame_index": frame_index,
                "recognized_at": recognized_at.isoformat(),
                "source": "attendance-service.attendance_pipeline",
            },
        )

        try:
            return await self.api_client.record_attendance(payload)
        except Exception:
            logger.exception(
                "Failed to record attendance on api-service: staff_id=%s employee_code=%s frame=%s",
                person.staff_id,
                person.employee_code,
                frame_index,
            )
            return None

    @staticmethod
    def _attendance_action_label(event_type: str | None) -> str:
        if event_type == "check_out":
            return "check-out"
        return "check-in"

    @staticmethod
    def _attendance_rejection_message(employee_code: str, reason: str | None) -> str:
        if reason == "EMPLOYEE_INACTIVE":
            return f"{employee_code}: nhân viên đang inactive"
        if reason == "NO_ACTIVE_SHIFT_ASSIGNMENT":
            return f"{employee_code}: chưa được gán ca làm việc"
        if reason:
            return f"{employee_code}: chưa ghi nhận ({reason})"
        return f"{employee_code}: chưa ghi nhận được"

    @staticmethod
    def _pipeline_failure_display(result: dict) -> tuple[str, str]:
        stage = result.get("stage")
        reason = str(result.get("reason") or "")

        if stage == "antispoof":
            return "spoof_detected", "Phát hiện giả mạo"
        if stage == "detect" and "Không phát hiện" in reason:
            return "no_face", "Không phát hiện khuôn mặt"
        if stage == "detect" and "Phát hiện" in reason:
            return "multiple_faces", "Phát hiện nhiều hơn 1 khuôn mặt"
        if stage == "quality":
            return "face_rejected", reason or "Khuôn mặt không hợp lệ"
        return "face_rejected", reason or "Khuôn mặt không hợp lệ"

    def _confirm_same_person(self, staff_id: str) -> bool:
        if staff_id == self._last_staff_id:
            self._consecutive_count += 1
        else:
            self._last_staff_id = staff_id
            self._consecutive_count = 1

        return self._consecutive_count >= 3

    def _reset_confirmation(self) -> None:
        self._last_staff_id = None
        self._consecutive_count = 0

    def _in_local_cooldown(self, staff_id: str) -> bool:
        self._cleanup_local_cooldown()
        last_seen = self._last_recognized_at.get(staff_id)
        if last_seen is None:
            return False

        elapsed = (datetime.now(timezone.utc) - last_seen).total_seconds()
        return elapsed < settings.attendance_recognized_pause_seconds

    def _mark_local_cooldown(self, staff_id: str) -> None:
        self._last_recognized_at[staff_id] = datetime.now(timezone.utc)

    def _cleanup_local_cooldown(self) -> None:
        now_mono = time.monotonic()
        if now_mono - self._last_cooldown_cleanup_mono < self._cooldown_cleanup_interval_seconds:
            return

        keep_after_seconds = max(settings.attendance_recognized_pause_seconds * 3, 60.0)
        now = datetime.now(timezone.utc)
        self._last_recognized_at = {
            staff_id: last_seen
            for staff_id, last_seen in self._last_recognized_at.items()
            if (now - last_seen).total_seconds() <= keep_after_seconds
        }
        self._last_cooldown_cleanup_mono = now_mono

    def _set_pause_after_recognized(self) -> None:
        pause_seconds = max(float(settings.attendance_recognized_pause_seconds), 0.0)
        if pause_seconds <= 0:
            return

        pause_until = time.monotonic() + pause_seconds
        with self._state_lock:
            if pause_until > self._pause_until_mono:
                self._pause_until_mono = pause_until

    def _get_pause_remaining_seconds(self) -> float:
        with self._state_lock:
            remaining = self._pause_until_mono - time.monotonic()
        return max(0.0, remaining)

    def get_latest_result(self) -> dict:
        with self._state_lock:
            result = dict(self._latest_result)

        updated_at = result.get("updated_at")
        if not updated_at:
            return result

        try:
            updated_dt = datetime.fromisoformat(updated_at)
        except ValueError:
            return result

        age = (datetime.now(timezone.utc) - updated_dt).total_seconds()
        if age > settings.attendance_recognition_result_max_age_seconds:
            return {
                "status": "scanning",
                "message": "Đang quét khuôn mặt",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        return result

    def get_latest_frame(self) -> FrameData | None:
        if self._reader is None:
            return None

        ok, frame_data = self._reader.latest()
        return frame_data if ok else None

    def get_annotated_frame_jpeg(self) -> bytes | None:
        frame_data = self.get_latest_frame()
        if frame_data is None:
            return None

        frame = frame_data.image.copy()
        self._draw_overlay(frame, self.get_latest_result())
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            return None
        return encoded.tobytes()

    def _set_latest_result(self, **values) -> None:
        values["updated_at"] = datetime.now(timezone.utc).isoformat()
        with self._state_lock:
            self._latest_result = values

    @staticmethod
    def _draw_overlay(frame, result: dict) -> None:
        status = result.get("status", "unknown")
        message = result.get("message", "")
        employee_code = result.get("employee_code")

        lines = []
        if employee_code:
            lines.append(str(employee_code))
        lines.append(str(message or AttendancePipeline._status_message(status)))

        face_box = AttendancePipeline._normalize_face_box(result.get("face_box"), frame.shape)
        color = AttendancePipeline._status_color(status)

        try:
            font = ImageFont.truetype(str(OVERLAY_FONT_PATH), 22)
            font_bold = ImageFont.truetype(str(OVERLAY_FONT_BOLD_PATH), 23)
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(image)

            if face_box is not None:
                AttendancePipeline._draw_face_box(draw, face_box, color)

            AttendancePipeline._draw_status_panel(
                draw=draw,
                frame_width=frame.shape[1],
                lines=lines,
                color=color,
                font=font,
                font_bold=font_bold,
                status=status,
            )

            frame[:] = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        except Exception:
            logger.exception("Failed to draw unicode overlay; falling back to OpenCV text")
            AttendancePipeline._draw_overlay_cv2(frame, lines, face_box, color)

    @staticmethod
    def _status_message(status: str) -> str:
        if status == "recorded":
            return "Đã chấm công"
        if status in {"record_failed", "spoof_detected"}:
            return "Chưa ghi nhận được"
        if status in {"completed", "cooldown"}:
            return "Đã chấm công gần đây"
        if status in {"multiple_faces", "not_recognized", "face_rejected", "rejected"}:
            return "Chưa thể chấm công"
        if status in {"recording", "confirming"}:
            return "Đang ghi nhận..."
        return "Đang quét khuôn mặt"

    @staticmethod
    def _status_color(status: str) -> tuple[int, int, int]:
        if status == "recorded":
            return (34, 197, 94)
        if status in {"record_failed", "spoof_detected"}:
            return (239, 68, 68)
        if status in {
            "completed",
            "cooldown",
            "multiple_faces",
            "not_recognized",
            "face_rejected",
            "rejected",
        }:
            return (245, 158, 11)
        return (255, 255, 255)

    @staticmethod
    def _status_text_color(status: str) -> tuple[int, int, int]:
        if status in {"recorded", "record_failed", "spoof_detected"}:
            return (255, 255, 255)
        return (17, 24, 39)

    @staticmethod
    def _normalize_face_box(box, frame_shape) -> tuple[int, int, int, int] | None:
        if not box or len(box) != 4:
            return None

        height, width = frame_shape[:2]
        x1, y1, x2, y2 = (int(v) for v in box)
        x1 = max(0, min(x1, width - 1))
        y1 = max(0, min(y1, height - 1))
        x2 = max(0, min(x2, width - 1))
        y2 = max(0, min(y2, height - 1))
        if x2 <= x1 or y2 <= y1:
            return None
        return x1, y1, x2, y2

    @staticmethod
    def _draw_face_box(
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        color: tuple[int, int, int],
    ) -> None:
        x1, y1, x2, y2 = box
        for offset in range(4):
            draw.rounded_rectangle(
                (x1 - offset, y1 - offset, x2 + offset, y2 + offset),
                radius=12,
                outline=color,
                width=1,
            )

    @staticmethod
    def _draw_status_panel(
        *,
        draw: ImageDraw.ImageDraw,
        frame_width: int,
        lines: list[str],
        color: tuple[int, int, int],
        font: ImageFont.FreeTypeFont,
        font_bold: ImageFont.FreeTypeFont,
        status: str,
    ) -> None:
        line_height = 32
        padding_x = 16
        padding_y = 12
        text_width = max(draw.textlength(line, font=font_bold if idx == 0 else font) for idx, line in enumerate(lines))
        width = min(max(int(text_width) + padding_x * 2, 300), frame_width - 24)
        height = padding_y * 2 + line_height * len(lines)
        draw.rounded_rectangle(
            (12, 12, 12 + width, 12 + height),
            radius=10,
            fill=color,
        )
        text_color = AttendancePipeline._status_text_color(status)
        for idx, line in enumerate(lines):
            draw.text(
                (12 + padding_x, 12 + padding_y + idx * line_height),
                line,
                fill=text_color,
                font=font_bold if idx == 0 else font,
            )

    @staticmethod
    def _draw_overlay_cv2(
        frame,
        lines: list[str],
        face_box: tuple[int, int, int, int] | None,
        color_rgb: tuple[int, int, int],
    ) -> None:
        color_bgr = (color_rgb[2], color_rgb[1], color_rgb[0])
        if face_box is not None:
            x1, y1, x2, y2 = face_box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color_bgr, 4)
        panel_x, panel_y = 12, 12

        line_height = 28
        width = 360
        height = 20 + line_height * len(lines)
        cv2.rectangle(frame, (panel_x, panel_y), (panel_x + width, panel_y + height), color_bgr, -1)
        for idx, line in enumerate(lines):
            cv2.putText(
                frame,
                line,
                (panel_x + 12, panel_y + 28 + idx * line_height),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 0),
                2,
                cv2.LINE_AA,
            )

    @staticmethod
    def _frame_delay_seconds() -> float:
        fps = max(float(settings.attendance_process_fps), 0.1)
        return 1.0 / fps

    @staticmethod
    def _log_task_result(task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error(
                "Attendance worker task failed",
                exc_info=(type(exc), exc, exc.__traceback__),
            )
