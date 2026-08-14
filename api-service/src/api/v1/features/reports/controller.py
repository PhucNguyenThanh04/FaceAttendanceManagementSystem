from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from src.api.v1.features.reports import schemas
from src.api.v1.features.reports.service import ReportService, get_report_service
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import RoleName
from src.core.dependencies.auth import require_roles

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/attendance-summary",
    response_model=list[schemas.AttendanceSummaryRead],
)
async def get_attendance_summary(
    query: schemas.MonthlyReportQuery = Depends(),
    service: ReportService = Depends(get_report_service),
    current_user: User = Depends(
        require_roles(RoleName.admin, RoleName.hr, RoleName.manager)
    ),
) -> list[schemas.AttendanceSummaryRead]:
    return await service.attendance_summary(query, current_user)


@router.get(
    "/leave-summary",
    response_model=list[schemas.LeaveSummaryRead],
)
async def get_leave_summary(
    query: schemas.LeaveSummaryQuery = Depends(),
    service: ReportService = Depends(get_report_service),
    _: User = Depends(require_roles(RoleName.admin, RoleName.hr)),
) -> list[schemas.LeaveSummaryRead]:
    return await service.leave_summary(query)


@router.get(
    "/late-ranking",
    response_model=list[schemas.LateRankingRead],
)
async def get_late_ranking(
    query: schemas.LateRankingQuery = Depends(),
    service: ReportService = Depends(get_report_service),
    current_user: User = Depends(
        require_roles(RoleName.admin, RoleName.hr, RoleName.manager)
    ),
) -> list[schemas.LateRankingRead]:
    return await service.late_ranking(query, current_user)


@router.get(
    "/monthly/{employee_id}",
    response_model=schemas.EmployeeMonthlyReportRead,
)
async def get_employee_monthly_report(
    employee_id: uuid.UUID,
    query: schemas.EmployeeMonthlyReportQuery = Depends(),
    service: ReportService = Depends(get_report_service),
    current_user: User = Depends(
        require_roles(
            RoleName.admin,
            RoleName.hr,
            RoleName.manager,
            RoleName.employee,
        )
    ),
) -> schemas.EmployeeMonthlyReportRead:
    return await service.employee_monthly_report(
        employee_id=employee_id,
        query=query,
        current_user=current_user,
    )
