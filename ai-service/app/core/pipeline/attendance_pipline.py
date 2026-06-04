from __future__ import annotations

import asyncio
import contextlib
import threading
from datetime import datetime, timezone

import cv2

from app.core.configs.settings import settings
from app.core.pipeline.pipe_processor import PipelineProcessor
from app.core.utils_ml_pipeline.read_camera import FrameData, MJPEGReader
from app.core.vector_db.qdrant_repo import Vectordb
from app.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class AttendancePipeline:
    def __init__(
        self,
        pipline: PipelineProcessor,
        vectordb: Vectordb,
        camera_url: str,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.pipeline_processor = pipline
        self.vectordb = vectordb
        self.camera_url = camera_url
        self.loop = loop
        self._task: asyncio.Task | None = None
        self._reader: MJPEGReader | None = None
        self._running = False
        self._last_staff_id: str | None = None
        self._consecutive_count = 0
        self._last_recognized_at: dict[str, datetime] = {}
        self._state_lock = threading.Lock()
        self._latest_result: dict = {
            "status": "waiting",
            "message": "Waiting for camera",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def start(self) -> None:
        if self.is_running:
            logger.info("Attendance worker already running")
            return

        self._running = True
        self._task = self.loop.create_task(self.camera_loop())
        self._task.add_done_callback(self._log_task_result)
        logger.info("Attendance worker started")

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        logger.info("Attendance worker stopped")

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
        embedding = await asyncio.to_thread(
            self.pipeline_processor.get_embedding,
            frame_data.image,
        )
        if embedding is None:
            self._reset_confirmation()
            self._set_latest_result(
                status="scanning",
                message="Scanning for face",
                frame_index=frame_data.index,
            )
            return

        result = await self.vectordb.identify_person(embedding)
        if result.status != "recognized" or result.person is None:
            self._reset_confirmation()
            self._set_latest_result(
                status=result.status,
                message="Face not recognized",
                confidence=result.confidence,
                frame_index=frame_data.index,
            )
            return

        person = result.person
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
                message=f"{person.employee_code} recently recognized",
                staff_id=person.staff_id,
                employee_code=person.employee_code,
                confidence=result.confidence,
                consecutive_count=self._consecutive_count,
                frame_index=frame_data.index,
            )
            return

        self._mark_local_cooldown(person.staff_id)
        self._set_latest_result(
            status="recognized",
            message=f"Recognized {person.employee_code}",
            staff_id=person.staff_id,
            employee_code=person.employee_code,
            confidence=result.confidence,
            consecutive_count=self._consecutive_count,
            frame_index=frame_data.index,
        )
        logger.info(
            "Attendance recognized: staff_id=%s employee_code=%s confidence=%s frame=%s",
            person.staff_id,
            person.employee_code,
            result.confidence,
            frame_data.index,
        )

    @staticmethod
    def _is_attendance_candidate(person) -> bool:
        return (
            person.is_active
            and person.status == "active"
            and (person.profile_status is None or person.profile_status == "active")
        )

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
        last_seen = self._last_recognized_at.get(staff_id)
        if last_seen is None:
            return False

        elapsed = (datetime.now(timezone.utc) - last_seen).total_seconds()
        return elapsed < settings.attendance_recognized_pause_seconds

    def _mark_local_cooldown(self, staff_id: str) -> None:
        self._last_recognized_at[staff_id] = datetime.now(timezone.utc)

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

        lines = [f"Status: {status}"]
        if employee_code:
            lines.append(f"Employee: {employee_code}")
        if confidence is not None:
            lines.append(f"Confidence: {float(confidence):.3f}")
        if message:
            lines.append(str(message))

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
