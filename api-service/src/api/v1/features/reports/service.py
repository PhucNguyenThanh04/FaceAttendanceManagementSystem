from __future__ import annotations

import uuid
from collections import Counter
from datetime import date

from fastapi import Depends

from src.api.v1.features.reports import schemas
from src.api.v1.features.reports.repo import ReportRepo, get_report_repo
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import AttendanceRecordStatus
from src.core.security.authorization import (
    AuthorizationPolicy,
    get_authorization_policy,
)
from src.utils.exeptions import NotFoundException


class ReportService:
    def __init__(
        self,
        report_repo: ReportRepo,
        authorization_policy: AuthorizationPolicy,
    ):
        self.report_repo = report_repo
        self.authorization_policy = authorization_policy

    @staticmethod
    def _month_window(year: int, month: int) -> tuple[date, date]:
        period_start = date(year, month, 1)
        if month == 12:
            return period_start, date(year + 1, 1, 1)
        return period_start, date(year, month + 1, 1)

    @staticmethod
    def _year_window(year: int) -> tuple[date, date]:
        return date(year, 1, 1), date(year + 1, 1, 1)

    async def attendance_summary(
        self,
        query: schemas.MonthlyReportQuery,
        current_user: User,
    ) -> list[schemas.AttendanceSummaryRead]:
        period_start, period_end = self._month_window(query.year, query.month)
        rows = await self.report_repo.attendance_summary(
            period_start=period_start,
            period_end=period_end,
            department_id=query.department_id,
            visible_employee_ids=(
                await self.authorization_policy.get_viewable_employee_ids(current_user)
            ),
        )
        return [schemas.AttendanceSummaryRead.model_validate(row) for row in rows]

    async def leave_summary(
        self,
        query: schemas.LeaveSummaryQuery,
    ) -> list[schemas.LeaveSummaryRead]:
        if query.month is None:
            period_start, period_end = self._year_window(query.year)
        else:
            period_start, period_end = self._month_window(query.year, query.month)
        rows = await self.report_repo.leave_summary(
            period_start=period_start,
            period_end=period_end,
            department_id=query.department_id,
        )
        return [schemas.LeaveSummaryRead.model_validate(row) for row in rows]

    async def late_ranking(
        self,
        query: schemas.LateRankingQuery,
        current_user: User,
    ) -> list[schemas.LateRankingRead]:
        period_start, period_end = self._month_window(query.year, query.month)
        rows = await self.report_repo.late_ranking(
            period_start=period_start,
            period_end=period_end,
            department_id=query.department_id,
            limit=query.limit,
            visible_employee_ids=(
                await self.authorization_policy.get_viewable_employee_ids(current_user)
            ),
        )
        ranking: list[schemas.LateRankingRead] = []
        for rank, row in enumerate(rows, start=1):
            late_days = int(row["late_days"])
            total_late_minutes = int(row["total_late_minutes"])
            ranking.append(
                schemas.LateRankingRead(
                    rank=rank,
                    employee_id=row["employee_id"],
                    employee_code=row["employee_code"],
                    full_name=row["full_name"],
                    department_id=row["department_id"],
                    department_name=row["department_name"],
                    late_days=late_days,
                    total_late_minutes=total_late_minutes,
                    average_late_minutes=round(total_late_minutes / late_days, 2),
                )
            )
        return ranking

    async def employee_monthly_report(
        self,
        *,
        employee_id: uuid.UUID,
        query: schemas.EmployeeMonthlyReportQuery,
        current_user: User,
    ) -> schemas.EmployeeMonthlyReportRead:
        employee = await self.report_repo.get_employee_identity(employee_id)
        if employee is None:
            raise NotFoundException("Employee")

        await self.authorization_policy.ensure_can_view_employee(
            current_user,
            employee_id,
        )

        period_start, period_end = self._month_window(query.year, query.month)
        records = await self.report_repo.list_monthly_records(
            employee_id=employee_id,
            period_start=period_start,
            period_end=period_end,
        )

        late_statuses = {
            AttendanceRecordStatus.late,
            AttendanceRecordStatus.late_and_early_leave,
        }
        early_statuses = {
            AttendanceRecordStatus.early_leave,
            AttendanceRecordStatus.late_and_early_leave,
        }
        status_counts = Counter(record.status for record in records)

        return schemas.EmployeeMonthlyReportRead(
            employee_id=employee["employee_id"],
            employee_code=employee["employee_code"],
            full_name=employee["full_name"],
            department_id=employee["department_id"],
            department_name=employee["department_name"],
            year=query.year,
            month=query.month,
            total_records=len(records),
            present_days=status_counts[AttendanceRecordStatus.present],
            late_days=sum(record.status in late_statuses for record in records),
            early_leave_days=sum(record.status in early_statuses for record in records),
            absent_days=status_counts[AttendanceRecordStatus.absent],
            on_leave_days=status_counts[AttendanceRecordStatus.on_leave],
            holiday_days=status_counts[AttendanceRecordStatus.holiday],
            missing_check_in_days=status_counts[
                AttendanceRecordStatus.missing_check_in
            ],
            missing_check_out_days=status_counts[
                AttendanceRecordStatus.missing_check_out
            ],
            total_worked_minutes=sum(record.worked_minutes for record in records),
            total_late_minutes=sum(record.late_minutes for record in records),
            total_early_leave_minutes=sum(
                record.early_leave_minutes for record in records
            ),
            records=[
                schemas.MonthlyAttendanceDayRead.model_validate(
                    record, from_attributes=True
                )
                for record in records
            ],
        )


def get_report_service(
    report_repo: ReportRepo = Depends(get_report_repo),
    authorization_policy: AuthorizationPolicy = Depends(get_authorization_policy),
) -> ReportService:
    return ReportService(report_repo, authorization_policy)
