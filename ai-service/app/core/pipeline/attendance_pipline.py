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
        acquired, embedding = await asyncio.to_thread(
            self.pipeline_processor.try_get_embedding,
            frame_data.image,
        )
        if not acquired:
            logger.info(
                "Attendance frame not recognized: frame=%s reason=ml_pipeline_busy",
                frame_data.index,
            )
            self._set_latest_result(
                status="busy",
                message="ML pipeline busy",
                frame_index=frame_data.index,
            )
            return

        if embedding is None:
            logger.info(
                "Attendance frame not recognized: frame=%s reason=no_valid_face",
                frame_data.index,
            )
            self._reset_confirmation()
            self._set_latest_result(
                status="scanning",
                message="Scanning for face",
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
                status=result.status,
                message="Face not recognized",
                confidence=result.confidence,
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
                message="Employee is inactive",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
                frame_index=frame_data.index,
            )
            return

        if not self._confirm_same_person(person.staff_id):
            self._set_latest_result(
                status="confirming",
                message=f"Confirming {person.employee_code}",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
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
                message=f"Đã nhận diện {person.employee_code} nhưng chưa ghi nhận được",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
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
                consecutive_count=self._consecutive_count,
                frame_index=frame_data.index,
            )
        else:
            self._set_latest_result(
                status="record_failed",
                message=f"Đã nhận diện {person.employee_code} nhưng chưa ghi nhận được",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
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
                "source": "ai-service.attendance_pipeline",
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
                "message": "Scanning for face",
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
        confidence = result.get("confidence")

        lines = [f"Trạng thái: {status}"]
        if employee_code:
            lines.append(f"Nhân viên: {employee_code}")
        if confidence is not None:
            lines.append(f"Độ tin cậy: {float(confidence):.3f}")
        if message:
            lines.append(str(message))

        try:
            font = ImageFont.truetype(str(OVERLAY_FONT_PATH), 22)
            font_bold = ImageFont.truetype(str(OVERLAY_FONT_BOLD_PATH), 23)
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(image)

            x, y = 24, 22
            line_height = 34
            text_width = max(draw.textlength(line, font=font) for line in lines)
            width = int(min(max(text_width + 32, 430), frame.shape[1] - 24))
            height = 24 + line_height * len(lines)
            draw.rounded_rectangle(
                (12, 12, 12 + width, 12 + height),
                radius=10,
                fill=(0, 0, 0),
                outline=(0, 180, 255),
                width=2,
            )

            for idx, line in enumerate(lines):
                draw.text(
                    (x, y + idx * line_height),
                    line,
                    fill=(255, 255, 255),
                    font=font_bold if idx == 0 else font,
                )

            frame[:] = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        except Exception:
            logger.exception("Failed to draw unicode overlay; falling back to OpenCV text")
            x, y = 24, 32
            line_height = 30
            width = 430
            height = 24 + line_height * len(lines)
            cv2.rectangle(frame, (12, 12), (12 + width, 12 + height), (0, 0, 0), -1)
            cv2.rectangle(frame, (12, 12), (12 + width, 12 + height), (0, 180, 255), 2)
            for idx, line in enumerate(lines):
                cv2.putText(
                    frame,
                    line,
                    (x, y + idx * line_height),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (255, 255, 255),
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
