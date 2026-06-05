from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from fastapi import Depends
from redis.asyncio import Redis

from src.api.v1.features.attendance import schemas
from src.api.v1.features.attendance.models import AttendanceEvent, AttendanceRecord
from src.api.v1.features.attendance.repo import AttendanceRepo, get_attendance_repo
from src.api.v1.shared.enums import (
    AttendanceEventType,
    AttendanceRecordStatus,
    AttendanceSource,
)
from src.core.dependencies.dep import get_redis_client
from src.utils.exeptions import DatabaseException, NotFoundException
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)

COOLDOWN_SECONDS = 600
CHECK_IN_START = time(hour=8, minute=0)
CHECK_OUT_END = time(hour=17, minute=0)
REASON_DUPLICATE_ATTENDANCE = "DUPLICATE_ATTENDANCE"
REASON_ATTENDANCE_ALREADY_COMPLETED = "ATTENDANCE_ALREADY_COMPLETED"


class AttendanceService:
    def __init__(self, attendance_repo: AttendanceRepo, redis_client: Redis):
        self.attendance_repo = attendance_repo
        self.redis = redis_client

    @staticmethod
    def _cooldown_key(employee_id: uuid.UUID) -> str:
        return f"attendance:cooldown:{employee_id}"

    @staticmethod
    def _normalize_event_time(event_time: datetime | None) -> datetime:
        if event_time is None:
            return datetime.now(timezone.utc)
        if event_time.tzinfo is None:
            return event_time.replace(tzinfo=timezone.utc)
        return event_time

    @staticmethod
    def _minutes_after(start: time, value: datetime) -> int:
        threshold = value.replace(
            hour=start.hour,
            minute=start.minute,
            second=start.second,
            microsecond=start.microsecond,
        )
        seconds = (value - threshold).total_seconds()
        return max(0, int(seconds // 60))

    @staticmethod
    def _minutes_before(end: time, value: datetime) -> int:
        threshold = value.replace(
            hour=end.hour,
            minute=end.minute,
            second=end.second,
            microsecond=end.microsecond,
        )
        seconds = (threshold - value).total_seconds()
        return max(0, int(seconds // 60))

    @staticmethod
    def _worked_minutes(check_in_time: datetime, check_out_time: datetime) -> int:
        seconds = (check_out_time - check_in_time).total_seconds()
        return max(0, int(seconds // 60))

    @staticmethod
    def _status_for_check_out(late_minutes: int, early_leave_minutes: int) -> AttendanceRecordStatus:
        if late_minutes > 0 and early_leave_minutes > 0:
            return AttendanceRecordStatus.late_and_early_leave
        if early_leave_minutes > 0:
            return AttendanceRecordStatus.early_leave
        if late_minutes > 0:
            return AttendanceRecordStatus.late
        return AttendanceRecordStatus.present

    @staticmethod
    def _rejected_response(
        *,
        employee_id: uuid.UUID,
        event_time: datetime,
        reason: str,
        cooldown_ttl_seconds: int | None = None,
    ) -> schemas.AttendanceEventAcceptedResponse:
        return schemas.AttendanceEventAcceptedResponse(
            accepted=False,
            reason=reason,
            employee_id=employee_id,
            event_time=event_time,
            cooldown_ttl_seconds=cooldown_ttl_seconds,
        )

    async def create_event_from_ai(
        self,
        payload: schemas.AttendanceAIEventCreate,
    ) -> schemas.AttendanceEventAcceptedResponse:
        event_time = self._normalize_event_time(payload.event_time)
        employee_id = payload.employee_id

        if not await self.attendance_repo.employee_exists(employee_id):
            logger.warning("Attendance event employee not found: employee_id=%s", employee_id)
            raise NotFoundException("Employee")

        cooldown_key = self._cooldown_key(employee_id)
        cooldown_value = await self.redis.get(cooldown_key)
        if cooldown_value is not None:
            ttl = await self.redis.ttl(cooldown_key)
            logger.info(
                "Attendance rejected by cooldown: employee_id=%s ttl=%s",
                employee_id,
                ttl,
            )
            return self._rejected_response(
                employee_id=employee_id,
                event_time=event_time,
                reason=REASON_DUPLICATE_ATTENDANCE,
                cooldown_ttl_seconds=ttl if ttl and ttl > 0 else None,
            )

        work_date = event_time.date()
        record = await self.attendance_repo.get_record_by_employee_and_work_date(
            employee_id=employee_id,
            work_date=work_date,
        )

        if record is None or record.check_in_time is None:
            event_type = AttendanceEventType.check_in
        elif record.check_out_time is None:
            event_type = AttendanceEventType.check_out
        else:
            logger.info(
                "Attendance already completed: employee_id=%s work_date=%s record_id=%s",
                employee_id,
                work_date,
                record.record_id,
            )
            return self._rejected_response(
                employee_id=employee_id,
                event_time=event_time,
                reason=REASON_ATTENDANCE_ALREADY_COMPLETED,
            )

        event = AttendanceEvent(
            employee_id=employee_id,
            event_type=event_type,
            event_time=event_time,
            confidence_score=payload.confidence_score,
            anti_spoof_score=payload.anti_spoof_score,
            image_url=payload.image_url,
            raw_result=payload.raw_result,
            is_accepted=True,
            rejection_reason=None,
        )
        self.attendance_repo.add_event(event)

        if event_type == AttendanceEventType.check_in:
            if record is None:
                record = AttendanceRecord(
                    employee_id=employee_id,
                    shift_id=None,
                    work_date=self.attendance_repo.work_date_to_db_value(work_date),
                    status=AttendanceRecordStatus.present,
                    late_minutes=0,
                    early_leave_minutes=0,
                    worked_minutes=0,
                    source=AttendanceSource.face_recognition,
                )
                self.attendance_repo.add_record(record)

            late_minutes = self._minutes_after(CHECK_IN_START, event_time)
            record.check_in_time = event_time
            record.source = AttendanceSource.face_recognition
            record.late_minutes = late_minutes
            record.early_leave_minutes = record.early_leave_minutes or 0
            record.worked_minutes = 0
            record.status = (
                AttendanceRecordStatus.late
                if late_minutes > 0
                else AttendanceRecordStatus.present
            )
        else:
            if record is None or record.check_in_time is None:
                raise DatabaseException("Attendance record is missing check-in state")
            early_leave_minutes = self._minutes_before(CHECK_OUT_END, event_time)
            record.check_out_time = event_time
            record.source = AttendanceSource.face_recognition
            record.early_leave_minutes = early_leave_minutes
            record.worked_minutes = self._worked_minutes(record.check_in_time, event_time)
            record.status = self._status_for_check_out(
                late_minutes=record.late_minutes or 0,
                early_leave_minutes=early_leave_minutes,
            )

        try:
            await self.attendance_repo.flush()
            await self.attendance_repo.commit()
            await self.attendance_repo.refresh(event)
            await self.attendance_repo.refresh(record)
        except Exception as exc:
            await self.attendance_repo.rollback()
            logger.exception(
                "Failed to create attendance event: employee_id=%s event_type=%s",
                employee_id,
                event_type,
            )
            raise DatabaseException("Failed to create attendance event") from exc

        await self.redis.set(
            cooldown_key,
            str(event.event_id or event_time.isoformat()),
            ex=COOLDOWN_SECONDS,
        )
        logger.info(
            "Attendance accepted: employee_id=%s event_id=%s record_id=%s event_type=%s",
            employee_id,
            event.event_id,
            record.record_id,
            event_type,
        )

        return schemas.AttendanceEventAcceptedResponse(
            accepted=True,
            reason=None,
            employee_id=employee_id,
            event_id=event.event_id,
            record_id=record.record_id,
            event_type=event_type,
            event_time=event_time,
            work_date=work_date,
            check_in_time=record.check_in_time,
            check_out_time=record.check_out_time,
            late_minutes=record.late_minutes,
            early_leave_minutes=record.early_leave_minutes,
            worked_minutes=record.worked_minutes,
            status=record.status,
            cooldown_ttl_seconds=COOLDOWN_SECONDS,
        )

    async def list_events(
        self,
        query: schemas.AttendanceEventListQuery,
    ) -> list[schemas.AttendanceEventRead]:
        events = await self.attendance_repo.list_events(query)
        return [schemas.AttendanceEventRead.model_validate(event) for event in events]

    async def get_event(self, event_id: uuid.UUID) -> schemas.AttendanceEventRead:
        event = await self.attendance_repo.get_event_by_id(event_id)
        if event is None:
            logger.warning("Attendance event not found: event_id=%s", event_id)
            raise NotFoundException("Attendance event")
        return schemas.AttendanceEventRead.model_validate(event)


def get_attendance_service(
    attendance_repo: AttendanceRepo = Depends(get_attendance_repo),
    redis_client: Redis = Depends(get_redis_client),
) -> AttendanceService:
    return AttendanceService(attendance_repo=attendance_repo, redis_client=redis_client)
