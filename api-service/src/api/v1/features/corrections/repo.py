from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import Depends
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.features.attendance.models import AttendanceRecord
from src.api.v1.features.corrections import schemas
from src.api.v1.features.corrections.models import (
    AttendanceCorrectionLog,
    AttendanceCorrectionRequest,
)
from src.api.v1.features.shifts.models import EmployeeShiftAssignment, WorkShift
from src.api.v1.features.staff.models import Employee
from src.api.v1.shared.enums import (
    ApprovalAction,
    AttendanceRecordStatus,
    AttendanceSource,
    CorrectionRequestStatus,
)
from src.core.db.database import get_db
from src.core.exceptions import DatabaseException
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class CorrectionRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_employee_id_by_user_id(self, user_id: uuid.UUID) -> uuid.UUID | None:
        try:
            stmt = select(Employee.employee_id).where(Employee.user_id == user_id)
            return await self.db.scalar(stmt)
        except Exception as exc:
            logger.exception("Failed to get employee by user: user_id=%s", user_id)
            raise DatabaseException("Failed to get employee") from exc

    async def list_correction_requests(
        self,
        query: schemas.CorrectionListQuery,
        visible_employee_ids: set[uuid.UUID] | None = None,
    ) -> tuple[list[AttendanceCorrectionRequest], int]:
        try:
            stmt: Select = select(AttendanceCorrectionRequest)

            if query.employee_id is not None:
                stmt = stmt.where(
                    AttendanceCorrectionRequest.employee_id == query.employee_id
                )
            if query.status is not None:
                stmt = stmt.where(AttendanceCorrectionRequest.status == query.status)
            if query.requested_from is not None:
                stmt = stmt.where(
                    AttendanceCorrectionRequest.created_at >= query.requested_from
                )
            if query.requested_to is not None:
                stmt = stmt.where(
                    AttendanceCorrectionRequest.created_at <= query.requested_to
                )
            if visible_employee_ids is not None:
                if not visible_employee_ids:
                    return [], 0
                stmt = stmt.where(
                    AttendanceCorrectionRequest.employee_id.in_(visible_employee_ids)
                )

            count_stmt = select(func.count()).select_from(
                stmt.order_by(None).subquery()
            )
            total = int((await self.db.scalar(count_stmt)) or 0)

            stmt = stmt.order_by(
                AttendanceCorrectionRequest.created_at.desc(),
                AttendanceCorrectionRequest.request_id.desc(),
            )
            stmt = stmt.offset((query.page - 1) * query.page_size).limit(
                query.page_size
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all()), total
        except Exception as exc:
            logger.exception("Failed to list correction requests")
            raise DatabaseException("Failed to list correction requests") from exc

    async def get_correction_request_by_id(
        self,
        request_id: uuid.UUID,
    ) -> AttendanceCorrectionRequest | None:
        try:
            stmt = select(AttendanceCorrectionRequest).where(
                AttendanceCorrectionRequest.request_id == request_id
            )
            return await self.db.scalar(stmt)
        except Exception as exc:
            logger.exception(
                "Failed to get correction request: request_id=%s",
                request_id,
            )
            raise DatabaseException("Failed to get correction request") from exc

    async def get_correction_request_for_review(
        self,
        request_id: uuid.UUID,
    ) -> AttendanceCorrectionRequest | None:
        try:
            stmt = (
                select(AttendanceCorrectionRequest)
                .where(AttendanceCorrectionRequest.request_id == request_id)
                .with_for_update()
            )
            return await self.db.scalar(stmt)
        except Exception as exc:
            logger.exception(
                "Failed to lock correction request for review: request_id=%s",
                request_id,
            )
            raise DatabaseException("Failed to get correction request") from exc

    async def list_correction_request_logs(
        self,
        request_id: uuid.UUID,
    ) -> list[AttendanceCorrectionLog]:
        try:
            stmt = (
                select(AttendanceCorrectionLog)
                .where(AttendanceCorrectionLog.correction_request_id == request_id)
                .order_by(
                    AttendanceCorrectionLog.created_at.asc(),
                    AttendanceCorrectionLog.log_id.asc(),
                )
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            logger.exception(
                "Failed to list correction request logs: request_id=%s",
                request_id,
            )
            raise DatabaseException("Failed to list correction request logs") from exc

    async def get_attendance_record_by_id(
        self,
        record_id: uuid.UUID,
    ) -> AttendanceRecord | None:
        try:
            stmt = select(AttendanceRecord).where(
                AttendanceRecord.record_id == record_id
            )
            return await self.db.scalar(stmt)
        except Exception as exc:
            logger.exception("Failed to get attendance record: record_id=%s", record_id)
            raise DatabaseException("Failed to get attendance record") from exc

    async def get_attendance_record_by_work_date(
        self,
        *,
        employee_id: uuid.UUID,
        work_date: date,
    ) -> AttendanceRecord | None:
        try:
            stmt = select(AttendanceRecord).where(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.work_date == work_date,
            )
            return await self.db.scalar(stmt)
        except Exception as exc:
            logger.exception(
                "Failed to get attendance record: employee_id=%s work_date=%s",
                employee_id,
                work_date,
            )
            raise DatabaseException("Failed to get attendance record") from exc

    async def get_work_shift(self, shift_id: int) -> WorkShift | None:
        try:
            return await self.db.scalar(
                select(WorkShift).where(WorkShift.shift_id == shift_id)
            )
        except Exception as exc:
            logger.exception("Failed to get work shift: shift_id=%s", shift_id)
            raise DatabaseException("Failed to get work shift") from exc

    async def get_shift_for_employee(
        self,
        *,
        employee_id: uuid.UUID,
        work_date: date,
    ) -> WorkShift | None:
        try:
            stmt = (
                select(WorkShift)
                .join(
                    EmployeeShiftAssignment,
                    EmployeeShiftAssignment.shift_id == WorkShift.shift_id,
                )
                .where(
                    EmployeeShiftAssignment.employee_id == employee_id,
                    EmployeeShiftAssignment.effective_date <= work_date,
                    (
                        EmployeeShiftAssignment.end_date.is_(None)
                        | (EmployeeShiftAssignment.end_date >= work_date)
                    ),
                    WorkShift.is_active.is_(True),
                )
                .order_by(
                    EmployeeShiftAssignment.effective_date.desc(),
                    EmployeeShiftAssignment.assignment_id.desc(),
                )
                .limit(1)
            )
            return await self.db.scalar(stmt)
        except Exception as exc:
            logger.exception(
                "Failed to get employee shift: employee_id=%s work_date=%s",
                employee_id,
                work_date,
            )
            raise DatabaseException("Failed to get employee shift") from exc

    async def has_pending_request_for_record(
        self,
        *,
        employee_id: uuid.UUID,
        attendance_record_id: uuid.UUID,
    ) -> bool:
        try:
            stmt = select(AttendanceCorrectionRequest.request_id).where(
                AttendanceCorrectionRequest.employee_id == employee_id,
                AttendanceCorrectionRequest.attendance_record_id
                == attendance_record_id,
                AttendanceCorrectionRequest.status == CorrectionRequestStatus.pending,
            )
            return (await self.db.execute(stmt)).first() is not None
        except Exception as exc:
            logger.exception(
                "Failed to check pending correction request: employee_id=%s record_id=%s",
                employee_id,
                attendance_record_id,
            )
            raise DatabaseException(
                "Failed to check pending correction request"
            ) from exc

    async def create_correction_request(
        self,
        *,
        employee_id: uuid.UUID,
        payload: schemas.AttendanceCorrectionRequestCreate,
    ) -> AttendanceCorrectionRequest:
        correction_request = AttendanceCorrectionRequest(
            employee_id=employee_id,
            attendance_record_id=payload.attendance_record_id,
            requested_check_in=payload.requested_check_in,
            requested_check_out=payload.requested_check_out,
            reason=payload.reason.strip(),
            status=CorrectionRequestStatus.pending,
        )
        self.db.add(correction_request)

        try:
            await self.db.commit()
            await self.db.refresh(correction_request)
            return correction_request
        except Exception as exc:
            await self.db.rollback()
            logger.exception(
                "Failed to create correction request: employee_id=%s record_id=%s",
                employee_id,
                payload.attendance_record_id,
            )
            raise DatabaseException("Failed to create correction request") from exc

    async def update_correction_request(
        self,
        correction_request: AttendanceCorrectionRequest,
        payload: schemas.AttendanceCorrectionRequestUpdate,
    ) -> AttendanceCorrectionRequest:
        update_data = payload.model_dump(exclude_unset=True)
        editable_fields = {"requested_check_in", "requested_check_out", "reason"}
        changed = False

        for field in editable_fields:
            if field not in update_data:
                continue
            value = update_data[field]
            if field == "reason" and value is not None:
                value = value.strip()
            if getattr(correction_request, field) != value:
                setattr(correction_request, field, value)
                changed = True

        if changed:
            try:
                await self.db.commit()
                await self.db.refresh(correction_request)
            except Exception as exc:
                await self.db.rollback()
                logger.exception(
                    "Failed to update correction request: request_id=%s",
                    correction_request.request_id,
                )
                raise DatabaseException("Failed to update correction request") from exc

        return correction_request

    async def cancel_correction_request(
        self,
        correction_request: AttendanceCorrectionRequest,
    ) -> AttendanceCorrectionRequest:
        correction_request.status = CorrectionRequestStatus.cancelled
        try:
            await self.db.commit()
            await self.db.refresh(correction_request)
            return correction_request
        except Exception as exc:
            await self.db.rollback()
            logger.exception(
                "Failed to cancel correction request: request_id=%s",
                correction_request.request_id,
            )
            raise DatabaseException("Failed to cancel correction request") from exc

    async def review_correction_request(
        self,
        *,
        correction_request: AttendanceCorrectionRequest,
        reviewer_id: uuid.UUID,
        action: ApprovalAction,
        comment: str | None,
        rejection_reason: str | None,
        attendance_record: AttendanceRecord | None = None,
        shift: WorkShift | None = None,
        work_date: date | None = None,
        new_check_in: datetime | None = None,
        new_check_out: datetime | None = None,
        late_minutes: int = 0,
        early_leave_minutes: int = 0,
        worked_minutes: int = 0,
        record_status: AttendanceRecordStatus | None = None,
    ) -> AttendanceCorrectionRequest:
        if action == ApprovalAction.approved and (
            shift is None or work_date is None or record_status is None
        ):
            raise DatabaseException("Attendance values are incomplete for approval")

        old_check_in = attendance_record.check_in_time if attendance_record else None
        old_check_out = attendance_record.check_out_time if attendance_record else None

        log = AttendanceCorrectionLog(
            correction_request_id=correction_request.request_id,
            reviewer_id=reviewer_id,
            action=action,
            comment=comment.strip() if comment else None,
            old_check_in=old_check_in,
            old_check_out=old_check_out,
            new_check_in=new_check_in if action == ApprovalAction.approved else None,
            new_check_out=new_check_out if action == ApprovalAction.approved else None,
        )
        self.db.add(log)

        now = datetime.now(timezone.utc)
        if action == ApprovalAction.rejected:
            correction_request.status = CorrectionRequestStatus.rejected
            correction_request.reviewed_by = reviewer_id
            correction_request.reviewed_at = now
            correction_request.rejection_reason = (
                rejection_reason.strip() if rejection_reason else None
            )
        elif action == ApprovalAction.approved:
            assert shift is not None
            assert work_date is not None
            assert record_status is not None
            if attendance_record is None:
                attendance_record = AttendanceRecord(
                    employee_id=correction_request.employee_id,
                    shift_id=shift.shift_id,
                    work_date=work_date,
                    source=AttendanceSource.manual,
                    status=record_status,
                    late_minutes=late_minutes,
                    early_leave_minutes=early_leave_minutes,
                    worked_minutes=worked_minutes,
                )
                self.db.add(attendance_record)
            else:
                attendance_record.shift_id = shift.shift_id
                attendance_record.source = AttendanceSource.edited
                attendance_record.status = record_status
                attendance_record.late_minutes = late_minutes
                attendance_record.early_leave_minutes = early_leave_minutes
                attendance_record.worked_minutes = worked_minutes

            attendance_record.check_in_time = new_check_in
            attendance_record.check_out_time = new_check_out
            correction_request.status = CorrectionRequestStatus.approved
            correction_request.reviewed_by = reviewer_id
            correction_request.reviewed_at = now
            correction_request.rejection_reason = None

        try:
            if action == ApprovalAction.approved:
                assert attendance_record is not None
                await self.db.flush()
                correction_request.attendance_record_id = attendance_record.record_id
            await self.db.commit()
            await self.db.refresh(correction_request)
            return correction_request
        except Exception as exc:
            await self.db.rollback()
            logger.exception(
                "Failed to review correction request: request_id=%s reviewer_id=%s",
                correction_request.request_id,
                reviewer_id,
            )
            raise DatabaseException("Failed to review correction request") from exc


def get_correction_repo(db: AsyncSession = Depends(get_db)) -> CorrectionRepo:
    return CorrectionRepo(db)
