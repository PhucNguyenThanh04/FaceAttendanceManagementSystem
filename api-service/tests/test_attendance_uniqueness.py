from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime, time, timezone
from types import SimpleNamespace
from typing import cast

import pytest
from redis.asyncio import Redis
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError

from src.api.v1.features.attendance import schemas
from src.api.v1.features.attendance.models import AttendanceRecord
from src.api.v1.features.attendance.repo import AttendanceRepo
from src.api.v1.features.attendance.service import (
    REASON_DUPLICATE_ATTENDANCE,
    AttendanceService,
)
from src.api.v1.shared.enums import EmployeeStatus


class FakeRedis:
    def __init__(self, *, acquired: bool = True) -> None:
        self.acquired = acquired
        self.set_calls: list[tuple] = []
        self.release_calls = 0

    async def set(self, key, value, **kwargs):
        self.set_calls.append((key, value, kwargs))
        return self.acquired

    async def ttl(self, _key):
        return 300

    async def eval(self, _script, _key_count, _key, _token):
        self.release_calls += 1
        return 1


class FakeAttendanceRepo:
    def __init__(self, *, fail_with_integrity_error: bool = False) -> None:
        self.fail_with_integrity_error = fail_with_integrity_error
        self.rollback_calls = 0
        self.event = None
        self.record: object | None = None
        self.overnight_record: SimpleNamespace | None = None
        self.shift = SimpleNamespace(
            shift_id=1,
            start_time=time(8, 0),
            end_time=time(17, 0),
            is_overnight=False,
            late_threshold_minutes=0,
            early_leave_threshold_minutes=0,
        )

    @staticmethod
    def work_date_to_db_value(value: date) -> date:
        return value

    async def get_employee_status(self, _employee_id):
        return EmployeeStatus.active

    async def get_open_overnight_record_for_checkout(self, **_kwargs):
        return self.overnight_record

    async def get_record_by_employee_and_work_date(self, **_kwargs):
        return None

    async def get_current_shift_assignment(self, **_kwargs):
        return SimpleNamespace(shift=self.shift)

    def add_event(self, event):
        self.event = event

    def add_record(self, record):
        self.record = record

    async def flush(self):
        if self.fail_with_integrity_error:
            raise IntegrityError("INSERT", {}, Exception("duplicate"))
        assert self.event is not None
        assert self.record is not None
        self.event.event_id = uuid.uuid4()
        self.record.record_id = uuid.uuid4()

    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None

    async def rollback(self):
        self.rollback_calls += 1


def make_service(repo: FakeAttendanceRepo, redis: FakeRedis) -> AttendanceService:
    return AttendanceService(
        cast(AttendanceRepo, repo),
        cast(Redis, redis),
    )


def test_model_has_employee_work_date_unique_constraint() -> None:
    constraints = {
        constraint.name
        for constraint in AttendanceRecord.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_attendance_records_employee_work_date" in constraints


def test_work_date_is_stored_as_date() -> None:
    value = date(2026, 7, 21)
    assert AttendanceRepo.work_date_to_db_value(value) is value


def test_cooldown_acquisition_uses_atomic_set_nx_ex() -> None:
    repo = FakeAttendanceRepo()
    redis = FakeRedis(acquired=False)
    service = make_service(repo, redis)

    response = asyncio.run(
        service.create_event_from_ai(
            schemas.AttendanceAIEventCreate(employee_id=uuid.uuid4())
        )
    )

    assert response.accepted is False
    assert response.reason == REASON_DUPLICATE_ATTENDANCE
    _, _, options = redis.set_calls[0]
    assert options == {"nx": True, "ex": 600}


def test_integrity_error_is_mapped_to_duplicate_business_response() -> None:
    repo = FakeAttendanceRepo(fail_with_integrity_error=True)
    redis = FakeRedis()
    service = make_service(repo, redis)

    response = asyncio.run(
        service.create_event_from_ai(
            schemas.AttendanceAIEventCreate(
                employee_id=uuid.uuid4(),
                event_time=datetime(2026, 7, 21, 1, 0, tzinfo=timezone.utc),
            )
        )
    )

    assert response.accepted is False
    assert response.reason == REASON_DUPLICATE_ATTENDANCE
    assert repo.rollback_calls == 1
    assert redis.release_calls == 1


def test_overnight_checkout_keeps_previous_work_date() -> None:
    repo = FakeAttendanceRepo()
    repo.shift.is_overnight = True
    repo.shift.start_time = time(22, 0)
    repo.shift.end_time = time(6, 0)
    previous_day = date(2026, 7, 20)
    overnight_record = SimpleNamespace(
        record_id=uuid.uuid4(),
        employee_id=uuid.uuid4(),
        shift_id=repo.shift.shift_id,
        shift=repo.shift,
        work_date=previous_day,
        check_in_time=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
        check_out_time=None,
        late_minutes=0,
        early_leave_minutes=0,
        worked_minutes=0,
        status=None,
        source=None,
    )

    repo.overnight_record = overnight_record
    repo.record = overnight_record
    redis = FakeRedis()
    service = make_service(repo, redis)

    response = asyncio.run(
        service.create_event_from_ai(
            schemas.AttendanceAIEventCreate(
                employee_id=overnight_record.employee_id,
                event_time=datetime(2026, 7, 20, 23, 0, tzinfo=timezone.utc),
            )
        )
    )

    assert response.accepted is True
    assert response.work_date == previous_day


@pytest.mark.integration
def test_concurrent_inserts_against_real_postgresql() -> None:
    """Opt-in: TEST_DATABASE_URL must point to a migrated disposable PostgreSQL DB."""
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    database_url_value = cast(str, database_url)

    async def run() -> None:
        asyncpg = pytest.importorskip("asyncpg")
        database_url_asyncpg = database_url_value.replace(
            "postgresql+asyncpg://",
            "postgresql://",
            1,
        )
        admin = await asyncpg.connect(database_url_asyncpg)
        employee_a = uuid.uuid4()
        employee_b = uuid.uuid4()
        employee_code_a = f"UT{uuid.uuid4().hex[:10]}"
        employee_code_b = f"UT{uuid.uuid4().hex[:10]}"
        work_day = date(2026, 7, 21)

        async def insert_record(employee_id: uuid.UUID, record_day: date) -> str:
            connection = await asyncpg.connect(database_url_asyncpg)
            try:
                await connection.execute(
                    """
                    INSERT INTO attendance_records (
                        record_id, employee_id, work_date, status,
                        late_minutes, early_leave_minutes, worked_minutes, source
                    ) VALUES ($1, $2, $3, 'present', 0, 0, 0, 'manual')
                    """,
                    uuid.uuid4(),
                    employee_id,
                    record_day,
                )
                return "inserted"
            except asyncpg.UniqueViolationError:
                return "duplicate"
            finally:
                await connection.close()

        try:
            constraint_exists = await admin.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_attendance_records_employee_work_date'
                )
                """
            )
            assert constraint_exists, "Run Alembic upgrade before this integration test"

            await admin.executemany(
                """
                INSERT INTO employees (
                    employee_id, employee_code, full_name, status
                ) VALUES ($1, $2, $3, 'active')
                """,
                [
                    (employee_a, employee_code_a, "Uniqueness Test A"),
                    (employee_b, employee_code_b, "Uniqueness Test B"),
                ],
            )

            concurrent_results = await asyncio.gather(
                insert_record(employee_a, work_day),
                insert_record(employee_a, work_day),
            )
            assert sorted(concurrent_results) == ["duplicate", "inserted"]

            assert await insert_record(employee_a, work_day) == "duplicate"
            assert await insert_record(employee_b, work_day) == "inserted"
            assert await insert_record(employee_a, date(2026, 7, 22)) == "inserted"
        finally:
            await admin.execute(
                "DELETE FROM employees WHERE employee_id = ANY($1::uuid[])",
                [employee_a, employee_b],
            )
            await admin.close()

    asyncio.run(run())
