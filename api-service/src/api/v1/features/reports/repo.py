from __future__ import annotations

import uuid
from datetime import date

from fastapi import Depends
from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.features.attendance.models import AttendanceRecord
from src.api.v1.features.leaves.models import LeaveRequest
from src.api.v1.features.staff.models import Department, Employee
from src.api.v1.shared.enums import AttendanceRecordStatus, LeaveRequestStatus
from src.core.db.database import get_db
from src.utils.exeptions import DatabaseException
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class ReportRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _count_when(condition):
        return func.sum(case((condition, 1), else_=0))

    async def attendance_summary(
        self,
        *,
        period_start: date,
        period_end: date,
        department_id: int | None,
        visible_employee_ids: set[uuid.UUID] | None = None,
    ) -> list[dict]:
        record_join = and_(
            AttendanceRecord.employee_id == Employee.employee_id,
            AttendanceRecord.work_date >= period_start,
            AttendanceRecord.work_date < period_end,
        )
        stmt = (
            select(
                Department.department_id,
                Department.name.label("department_name"),
                func.count(distinct(Employee.employee_id)).label("employee_count"),
                func.count(AttendanceRecord.record_id).label("total_records"),
                self._count_when(
                    AttendanceRecord.status == AttendanceRecordStatus.present
                ).label("present_days"),
                self._count_when(
                    AttendanceRecord.status.in_(
                        [
                            AttendanceRecordStatus.late,
                            AttendanceRecordStatus.late_and_early_leave,
                        ]
                    )
                ).label("late_days"),
                self._count_when(
                    AttendanceRecord.status.in_(
                        [
                            AttendanceRecordStatus.early_leave,
                            AttendanceRecordStatus.late_and_early_leave,
                        ]
                    )
                ).label("early_leave_days"),
                self._count_when(
                    AttendanceRecord.status == AttendanceRecordStatus.absent
                ).label("absent_days"),
                self._count_when(
                    AttendanceRecord.status == AttendanceRecordStatus.on_leave
                ).label("on_leave_days"),
                self._count_when(
                    AttendanceRecord.status == AttendanceRecordStatus.holiday
                ).label("holiday_days"),
                self._count_when(
                    AttendanceRecord.status == AttendanceRecordStatus.missing_check_in
                ).label("missing_check_in_days"),
                self._count_when(
                    AttendanceRecord.status == AttendanceRecordStatus.missing_check_out
                ).label("missing_check_out_days"),
                func.coalesce(func.sum(AttendanceRecord.worked_minutes), 0).label(
                    "total_worked_minutes"
                ),
                func.coalesce(func.sum(AttendanceRecord.late_minutes), 0).label(
                    "total_late_minutes"
                ),
                func.coalesce(func.sum(AttendanceRecord.early_leave_minutes), 0).label(
                    "total_early_leave_minutes"
                ),
            )
            .select_from(Department)
            .outerjoin(Employee, Employee.department_id == Department.department_id)
            .outerjoin(AttendanceRecord, record_join)
            .group_by(Department.department_id, Department.name)
            .order_by(Department.name.asc())
        )
        if department_id is not None:
            stmt = stmt.where(Department.department_id == department_id)
        if visible_employee_ids is not None:
            if not visible_employee_ids:
                return []
            stmt = stmt.where(Employee.employee_id.in_(visible_employee_ids))

        try:
            result = await self.db.execute(stmt)
            return [dict(row) for row in result.mappings().all()]
        except Exception as exc:
            logger.exception("Failed to build attendance summary")
            raise DatabaseException("Failed to build attendance summary") from exc

    async def leave_summary(
        self,
        *,
        period_start: date,
        period_end: date,
        department_id: int | None,
    ) -> list[dict]:
        request_join = and_(
            LeaveRequest.employee_id == Employee.employee_id,
            LeaveRequest.start_date >= period_start,
            LeaveRequest.start_date < period_end,
        )
        stmt = (
            select(
                Department.department_id,
                Department.name.label("department_name"),
                func.count(distinct(Employee.employee_id)).label("employee_count"),
                func.count(LeaveRequest.request_id).label("total_requests"),
                self._count_when(
                    LeaveRequest.status == LeaveRequestStatus.pending
                ).label("pending_requests"),
                self._count_when(
                    LeaveRequest.status == LeaveRequestStatus.approved
                ).label("approved_requests"),
                self._count_when(
                    LeaveRequest.status == LeaveRequestStatus.rejected
                ).label("rejected_requests"),
                self._count_when(
                    LeaveRequest.status == LeaveRequestStatus.cancelled
                ).label("cancelled_requests"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                LeaveRequest.status == LeaveRequestStatus.approved,
                                func.coalesce(LeaveRequest.total_days, 0.0),
                            ),
                            else_=0.0,
                        )
                    ),
                    0.0,
                ).label("approved_leave_days"),
            )
            .select_from(Department)
            .outerjoin(Employee, Employee.department_id == Department.department_id)
            .outerjoin(LeaveRequest, request_join)
            .group_by(Department.department_id, Department.name)
            .order_by(Department.name.asc())
        )
        if department_id is not None:
            stmt = stmt.where(Department.department_id == department_id)

        try:
            result = await self.db.execute(stmt)
            return [dict(row) for row in result.mappings().all()]
        except Exception as exc:
            logger.exception("Failed to build leave summary")
            raise DatabaseException("Failed to build leave summary") from exc

    async def late_ranking(
        self,
        *,
        period_start: date,
        period_end: date,
        department_id: int | None,
        limit: int,
        visible_employee_ids: set[uuid.UUID] | None = None,
    ) -> list[dict]:
        stmt = (
            select(
                Employee.employee_id,
                Employee.employee_code,
                Employee.full_name,
                Department.department_id,
                Department.name.label("department_name"),
                func.count(AttendanceRecord.record_id).label("late_days"),
                func.coalesce(func.sum(AttendanceRecord.late_minutes), 0).label(
                    "total_late_minutes"
                ),
            )
            .select_from(AttendanceRecord)
            .join(Employee, Employee.employee_id == AttendanceRecord.employee_id)
            .outerjoin(Department, Department.department_id == Employee.department_id)
            .where(
                AttendanceRecord.work_date >= period_start,
                AttendanceRecord.work_date < period_end,
                AttendanceRecord.late_minutes > 0,
            )
            .group_by(
                Employee.employee_id,
                Employee.employee_code,
                Employee.full_name,
                Department.department_id,
                Department.name,
            )
            .order_by(
                func.sum(AttendanceRecord.late_minutes).desc(),
                func.count(AttendanceRecord.record_id).desc(),
                Employee.employee_code.asc(),
            )
            .limit(limit)
        )
        if department_id is not None:
            stmt = stmt.where(Employee.department_id == department_id)
        if visible_employee_ids is not None:
            if not visible_employee_ids:
                return []
            stmt = stmt.where(Employee.employee_id.in_(visible_employee_ids))

        try:
            result = await self.db.execute(stmt)
            return [dict(row) for row in result.mappings().all()]
        except Exception as exc:
            logger.exception("Failed to build late ranking")
            raise DatabaseException("Failed to build late ranking") from exc

    async def get_employee_identity(self, employee_id: uuid.UUID) -> dict | None:
        stmt = (
            select(
                Employee.employee_id,
                Employee.user_id,
                Employee.employee_code,
                Employee.full_name,
                Employee.department_id,
                Department.name.label("department_name"),
            )
            .select_from(Employee)
            .outerjoin(Department, Department.department_id == Employee.department_id)
            .where(Employee.employee_id == employee_id)
        )
        try:
            row = (await self.db.execute(stmt)).mappings().one_or_none()
            return dict(row) if row is not None else None
        except Exception as exc:
            logger.exception(
                "Failed to get report employee: employee_id=%s", employee_id
            )
            raise DatabaseException("Failed to get report employee") from exc

    async def list_monthly_records(
        self,
        *,
        employee_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> list[AttendanceRecord]:
        stmt = (
            select(AttendanceRecord)
            .where(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.work_date >= period_start,
                AttendanceRecord.work_date < period_end,
            )
            .order_by(AttendanceRecord.work_date.asc())
        )
        try:
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            logger.exception(
                "Failed to list monthly report records: employee_id=%s",
                employee_id,
            )
            raise DatabaseException("Failed to build employee monthly report") from exc


def get_report_repo(db: AsyncSession = Depends(get_db)) -> ReportRepo:
    return ReportRepo(db)
