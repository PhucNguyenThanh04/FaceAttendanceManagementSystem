from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta

from fastapi import Depends
from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.v1.features.attendance.models import AttendanceEvent, AttendanceRecord
from src.api.v1.features.attendance import schemas
from src.api.v1.features.shifts.models import EmployeeShiftAssignment, WorkShift
from src.api.v1.features.staff.models import Employee
from src.api.v1.shared.enums import EmployeeStatus
from src.core.db.database import get_db


class AttendanceRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def work_date_to_db_value(work_date: date) -> datetime:
        # Current schema stores work_date as DateTime, so normalize date to midnight.
        return datetime.combine(work_date, time.min)

    async def employee_exists(self, employee_id: uuid.UUID) -> bool:
        stmt = select(Employee.employee_id).where(Employee.employee_id == employee_id)
        return (await self.db.execute(stmt)).first() is not None

    async def get_employee_status(self, employee_id: uuid.UUID) -> EmployeeStatus | None:
        stmt = select(Employee.status).where(Employee.employee_id == employee_id)
        return await self.db.scalar(stmt)

    async def get_event_by_id(self, event_id: uuid.UUID) -> AttendanceEvent | None:
        return await self.db.scalar(
            select(AttendanceEvent).where(AttendanceEvent.event_id == event_id)
        )

    async def list_events(
        self,
        query: schemas.AttendanceEventListQuery,
    ) -> list[AttendanceEvent]:
        stmt: Select = select(AttendanceEvent)

        if query.employee_id is not None:
            stmt = stmt.where(AttendanceEvent.employee_id == query.employee_id)
        if query.event_type is not None:
            stmt = stmt.where(AttendanceEvent.event_type == query.event_type)
        if query.accepted is not None:
            stmt = stmt.where(AttendanceEvent.is_accepted.is_(query.accepted))
        if query.event_time_from is not None:
            stmt = stmt.where(AttendanceEvent.event_time >= query.event_time_from)
        if query.event_time_to is not None:
            stmt = stmt.where(AttendanceEvent.event_time <= query.event_time_to)

        stmt = stmt.order_by(AttendanceEvent.event_time.desc(), AttendanceEvent.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_record_by_employee_and_work_date(
        self,
        employee_id: uuid.UUID,
        work_date: date,
    ) -> AttendanceRecord | None:
        work_date_value = self.work_date_to_db_value(work_date)
        stmt = (
            select(AttendanceRecord)
            .options(selectinload(AttendanceRecord.shift))
            .where(
                and_(
                    AttendanceRecord.employee_id == employee_id,
                    AttendanceRecord.work_date == work_date_value,
                )
            )
        )
        return await self.db.scalar(stmt)

    async def get_current_shift_assignment(
        self,
        employee_id: uuid.UUID,
        as_of: date,
    ) -> EmployeeShiftAssignment | None:
        stmt = (
            select(EmployeeShiftAssignment)
            .join(WorkShift, EmployeeShiftAssignment.shift_id == WorkShift.shift_id)
            .options(selectinload(EmployeeShiftAssignment.shift))
            .where(
                EmployeeShiftAssignment.employee_id == employee_id,
                EmployeeShiftAssignment.effective_date <= as_of,
                WorkShift.is_active.is_(True),
                (
                    (EmployeeShiftAssignment.end_date.is_(None))
                    | (EmployeeShiftAssignment.end_date >= as_of)
                ),
            )
            .order_by(
                EmployeeShiftAssignment.effective_date.desc(),
                EmployeeShiftAssignment.assignment_id.desc(),
            )
            .limit(1)
        )
        return await self.db.scalar(stmt)

    async def get_open_overnight_record_for_checkout(
        self,
        employee_id: uuid.UUID,
        event_date: date,
    ) -> AttendanceRecord | None:
        previous_work_date = self.work_date_to_db_value(event_date - timedelta(days=1))
        stmt = (
            select(AttendanceRecord)
            .join(WorkShift, AttendanceRecord.shift_id == WorkShift.shift_id)
            .options(selectinload(AttendanceRecord.shift))
            .where(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.work_date == previous_work_date,
                AttendanceRecord.check_in_time.is_not(None),
                AttendanceRecord.check_out_time.is_(None),
                WorkShift.is_overnight.is_(True),
            )
            .limit(1)
        )
        return await self.db.scalar(stmt)

    def add_event(self, event: AttendanceEvent) -> None:
        self.db.add(event)

    def add_record(self, record: AttendanceRecord) -> None:
        self.db.add(record)

    async def flush(self) -> None:
        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()

    async def refresh(self, obj) -> None:
        await self.db.refresh(obj)


def get_attendance_repo(db: AsyncSession = Depends(get_db)) -> AttendanceRepo:
    return AttendanceRepo(db)
