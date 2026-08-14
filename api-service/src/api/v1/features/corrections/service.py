from __future__ import annotations

import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import Depends

from src.api.v1.features.attendance.service import AttendanceService
from src.api.v1.features.corrections import schemas
from src.api.v1.features.corrections.repo import CorrectionRepo, get_correction_repo
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import (
    ApprovalAction,
    AttendanceRecordStatus,
    CorrectionRequestStatus,
    RoleName,
)
from src.core.configs.settings import settings
from src.core.exceptions import (
    AppException,
    ConflictException,
    DatabaseException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.core.security.authorization import (
    AuthorizationPolicy,
    get_authorization_policy,
)
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)
APP_TZ = ZoneInfo(settings.database_timezone)


class CorrectionService:
    def __init__(
        self,
        correction_repo: CorrectionRepo,
        authorization_policy: AuthorizationPolicy,
    ):
        self.correction_repo = correction_repo
        self.authorization_policy = authorization_policy

    @staticmethod
    def _to_read(
        correction_request,
    ) -> schemas.AttendanceCorrectionRequestRead:
        return schemas.AttendanceCorrectionRequestRead.model_validate(
            correction_request
        )

    @staticmethod
    def _to_app_timezone(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=APP_TZ)
        return value.astimezone(APP_TZ)

    @classmethod
    def _work_date_from_time(cls, value: datetime) -> date:
        return cls._to_app_timezone(value).date()

    async def list_correction_requests(
        self,
        *,
        query: schemas.CorrectionListQuery,
        current_user: User,
    ) -> schemas.CorrectionListResponse:
        try:
            visible_employee_ids = (
                await self.authorization_policy.scope_for_employee_query(
                    current_user,
                    query.employee_id,
                )
            )

            (
                correction_requests,
                total,
            ) = await self.correction_repo.list_correction_requests(
                query,
                visible_employee_ids=visible_employee_ids,
            )
            return schemas.CorrectionListResponse(
                items=[self._to_read(item) for item in correction_requests],
                total=total,
                page=query.page,
                page_size=query.page_size,
            )
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Failed to list correction requests")
            raise DatabaseException("Failed to list correction requests") from exc

    async def get_correction_request(
        self,
        *,
        request_id: uuid.UUID,
        current_user: User,
    ) -> schemas.AttendanceCorrectionRequestRead:
        try:
            correction_request = (
                await self.correction_repo.get_correction_request_by_id(request_id)
            )
            if correction_request is None:
                raise NotFoundException("Correction request")

            await self.authorization_policy.ensure_can_view_employee(
                current_user,
                correction_request.employee_id,
            )

            return self._to_read(correction_request)
        except AppException:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to get correction request: request_id=%s",
                request_id,
            )
            raise DatabaseException("Failed to get correction request") from exc

    async def create_correction_request(
        self,
        *,
        employee_id: uuid.UUID,
        payload: schemas.AttendanceCorrectionRequestCreate,
    ) -> schemas.AttendanceCorrectionRequestRead:
        try:
            if len(payload.reason.strip()) < 3:
                raise ValidationException(
                    "reason must contain at least 3 non-whitespace characters"
                )

            attendance_record = None
            if payload.attendance_record_id is not None:
                attendance_record = (
                    await self.correction_repo.get_attendance_record_by_id(
                        payload.attendance_record_id
                    )
                )
                if attendance_record is None:
                    raise NotFoundException("Attendance record")
                if attendance_record.employee_id != employee_id:
                    raise ForbiddenException(
                        "You can only request a correction for your own attendance record"
                    )

                if await self.correction_repo.has_pending_request_for_record(
                    employee_id=employee_id,
                    attendance_record_id=payload.attendance_record_id,
                ):
                    raise ConflictException(
                        "A pending correction request already exists for this attendance record"
                    )

                effective_check_in = (
                    payload.requested_check_in
                    if payload.requested_check_in is not None
                    else attendance_record.check_in_time
                )
                effective_check_out = (
                    payload.requested_check_out
                    if payload.requested_check_out is not None
                    else attendance_record.check_out_time
                )
                if (
                    effective_check_in is not None
                    and effective_check_out is not None
                    and effective_check_out < effective_check_in
                ):
                    raise ValidationException(
                        "The requested check times are inconsistent with the attendance record"
                    )

            correction_request = await self.correction_repo.create_correction_request(
                employee_id=employee_id,
                payload=payload,
            )
            logger.info(
                "Correction request created: request_id=%s employee_id=%s record_id=%s",
                correction_request.request_id,
                employee_id,
                payload.attendance_record_id,
            )
            return self._to_read(correction_request)
        except AppException:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to create correction request: employee_id=%s",
                employee_id,
            )
            raise DatabaseException("Failed to create correction request") from exc

    async def update_pending_correction_request(
        self,
        *,
        request_id: uuid.UUID,
        payload: schemas.AttendanceCorrectionRequestUpdate,
        employee_id: uuid.UUID,
    ) -> schemas.AttendanceCorrectionRequestRead:
        try:
            correction_request = (
                await self.correction_repo.get_correction_request_by_id(request_id)
            )
            if correction_request is None:
                raise NotFoundException("Correction request")
            if correction_request.employee_id != employee_id:
                raise ForbiddenException(
                    "You can only update your own correction requests"
                )
            if correction_request.status != CorrectionRequestStatus.pending:
                raise ConflictException(
                    "Only pending correction requests can be updated"
                )

            forbidden_fields = {
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
            }
            touched_forbidden_fields = forbidden_fields.intersection(
                payload.model_fields_set
            )
            if touched_forbidden_fields:
                raise ValidationException(
                    f"{', '.join(sorted(touched_forbidden_fields))} cannot be updated here"
                )

            effective_check_in = (
                payload.requested_check_in
                if "requested_check_in" in payload.model_fields_set
                else correction_request.requested_check_in
            )
            effective_check_out = (
                payload.requested_check_out
                if "requested_check_out" in payload.model_fields_set
                else correction_request.requested_check_out
            )
            if effective_check_in is None and effective_check_out is None:
                raise ValidationException(
                    "At least one of requested_check_in or requested_check_out is required"
                )
            if (
                effective_check_in is not None
                and effective_check_out is not None
                and effective_check_out < effective_check_in
            ):
                raise ValidationException(
                    "requested_check_out must be on/after requested_check_in"
                )

            if correction_request.attendance_record_id is not None:
                attendance_record = (
                    await self.correction_repo.get_attendance_record_by_id(
                        correction_request.attendance_record_id
                    )
                )
                if attendance_record is not None:
                    final_check_in = (
                        effective_check_in or attendance_record.check_in_time
                    )
                    final_check_out = (
                        effective_check_out or attendance_record.check_out_time
                    )
                    if (
                        final_check_in is not None
                        and final_check_out is not None
                        and final_check_out < final_check_in
                    ):
                        raise ValidationException(
                            "The requested check times are inconsistent with the attendance record"
                        )

            if "reason" in payload.model_fields_set:
                if payload.reason is None or len(payload.reason.strip()) < 3:
                    raise ValidationException(
                        "reason must contain at least 3 non-whitespace characters"
                    )

            updated = await self.correction_repo.update_correction_request(
                correction_request,
                payload,
            )
            logger.info("Correction request updated: request_id=%s", request_id)
            return self._to_read(updated)
        except AppException:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to update correction request: request_id=%s",
                request_id,
            )
            raise DatabaseException("Failed to update correction request") from exc

    async def cancel_correction_request(
        self,
        *,
        request_id: uuid.UUID,
        employee_id: uuid.UUID,
    ) -> schemas.AttendanceCorrectionRequestRead:
        try:
            correction_request = (
                await self.correction_repo.get_correction_request_by_id(request_id)
            )
            if correction_request is None:
                raise NotFoundException("Correction request")
            if correction_request.employee_id != employee_id:
                raise ForbiddenException(
                    "You can only cancel your own correction requests"
                )
            if correction_request.status != CorrectionRequestStatus.pending:
                raise ConflictException(
                    "Only pending correction requests can be cancelled"
                )

            cancelled = await self.correction_repo.cancel_correction_request(
                correction_request
            )
            logger.info(
                "Correction request cancelled: request_id=%s employee_id=%s",
                request_id,
                employee_id,
            )
            return self._to_read(cancelled)
        except AppException:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to cancel correction request: request_id=%s",
                request_id,
            )
            raise DatabaseException("Failed to cancel correction request") from exc

    async def review_correction_request(
        self,
        *,
        request_id: uuid.UUID,
        payload: schemas.ReviewCorrectionRequest,
        reviewer_id: uuid.UUID,
        reviewer_role: RoleName,
        current_user: User,
    ) -> schemas.AttendanceCorrectionRequestRead:
        try:
            if reviewer_role == RoleName.manager:
                if payload.action not in {
                    ApprovalAction.forwarded,
                    ApprovalAction.rejected,
                }:
                    raise ValidationException(
                        "Managers can only forward or reject correction requests"
                    )
            elif payload.action not in {
                ApprovalAction.approved,
                ApprovalAction.rejected,
            }:
                raise ValidationException(
                    "HR and admin can only approve or reject correction requests"
                )

            if (
                payload.action == ApprovalAction.rejected
                and not (payload.rejection_reason or "").strip()
            ):
                raise ValidationException(
                    "rejection_reason is required when action=rejected"
                )

            correction_request = (
                await self.correction_repo.get_correction_request_for_review(request_id)
            )
            if correction_request is None:
                raise NotFoundException("Correction request")
            if correction_request.status != CorrectionRequestStatus.pending:
                raise ConflictException(
                    "Only pending correction requests can be reviewed"
                )

            await self.authorization_policy.ensure_can_view_employee(
                current_user,
                correction_request.employee_id,
            )

            attendance_record = None
            if correction_request.attendance_record_id is not None:
                attendance_record = (
                    await self.correction_repo.get_attendance_record_by_id(
                        correction_request.attendance_record_id
                    )
                )
                if attendance_record is None:
                    raise NotFoundException("Attendance record")
                if attendance_record.employee_id != correction_request.employee_id:
                    raise ValidationException(
                        "Attendance record does not belong to the request owner"
                    )

            if payload.action != ApprovalAction.approved:
                reviewed = await self.correction_repo.review_correction_request(
                    correction_request=correction_request,
                    reviewer_id=reviewer_id,
                    action=payload.action,
                    comment=payload.comment,
                    rejection_reason=payload.rejection_reason,
                    attendance_record=attendance_record,
                )
                logger.info(
                    "Correction request reviewed: request_id=%s reviewer_id=%s action=%s",
                    request_id,
                    reviewer_id,
                    payload.action,
                )
                return self._to_read(reviewed)

            proposed_check_in = (
                payload.approved_check_in or correction_request.requested_check_in
            )
            proposed_check_out = (
                payload.approved_check_out or correction_request.requested_check_out
            )
            reference_time = proposed_check_in or proposed_check_out
            if reference_time is None:
                raise ValidationException(
                    "At least one approved check time is required"
                )

            if attendance_record is None:
                proposed_work_date = self._work_date_from_time(reference_time)
                attendance_record = (
                    await self.correction_repo.get_attendance_record_by_work_date(
                        employee_id=correction_request.employee_id,
                        work_date=proposed_work_date,
                    )
                )

            new_check_in = (
                payload.approved_check_in
                or correction_request.requested_check_in
                or (attendance_record.check_in_time if attendance_record else None)
            )
            new_check_out = (
                payload.approved_check_out
                or correction_request.requested_check_out
                or (attendance_record.check_out_time if attendance_record else None)
            )
            if new_check_in is None and new_check_out is None:
                raise ValidationException(
                    "At least one approved check time is required"
                )
            effective_check_time = (
                new_check_in if new_check_in is not None else new_check_out
            )
            assert effective_check_time is not None
            calculation_check_in = (
                self._to_app_timezone(new_check_in)
                if new_check_in is not None
                else None
            )
            calculation_check_out = (
                self._to_app_timezone(new_check_out)
                if new_check_out is not None
                else None
            )
            if (
                calculation_check_in is not None
                and calculation_check_out is not None
                and calculation_check_out < calculation_check_in
            ):
                raise ValidationException(
                    "approved_check_out must be on/after approved_check_in"
                )

            if attendance_record is not None:
                work_date = attendance_record.work_date
                if isinstance(work_date, datetime):
                    work_date = work_date.date()
            else:
                work_date = self._work_date_from_time(effective_check_time)
            shift = None
            if attendance_record is not None and attendance_record.shift_id is not None:
                shift = await self.correction_repo.get_work_shift(
                    attendance_record.shift_id
                )
            if shift is None:
                shift = await self.correction_repo.get_shift_for_employee(
                    employee_id=correction_request.employee_id,
                    work_date=work_date,
                )
            if shift is None:
                raise ValidationException(
                    "No active work shift found for the correction date"
                )

            late_minutes = 0
            early_leave_minutes = 0
            worked_minutes = 0
            if calculation_check_in is not None:
                late_minutes = AttendanceService._late_minutes(
                    shift,
                    work_date,
                    calculation_check_in,
                )
            if calculation_check_out is not None:
                early_leave_minutes = AttendanceService._early_leave_minutes(
                    shift,
                    work_date,
                    calculation_check_out,
                )
            if calculation_check_in is not None and calculation_check_out is not None:
                worked_minutes = AttendanceService._worked_minutes(
                    calculation_check_in,
                    calculation_check_out,
                )
                record_status = AttendanceService._status_for_check_out(
                    late_minutes,
                    early_leave_minutes,
                )
            elif calculation_check_in is not None:
                record_status = AttendanceRecordStatus.missing_check_out
            else:
                record_status = AttendanceRecordStatus.missing_check_in

            reviewed = await self.correction_repo.review_correction_request(
                correction_request=correction_request,
                reviewer_id=reviewer_id,
                action=payload.action,
                comment=payload.comment,
                rejection_reason=None,
                attendance_record=attendance_record,
                shift=shift,
                work_date=work_date,
                new_check_in=new_check_in,
                new_check_out=new_check_out,
                late_minutes=late_minutes,
                early_leave_minutes=early_leave_minutes,
                worked_minutes=worked_minutes,
                record_status=record_status,
            )
            logger.info(
                "Correction request approved and applied: request_id=%s reviewer_id=%s",
                request_id,
                reviewer_id,
            )
            return self._to_read(reviewed)
        except AppException:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to review correction request: request_id=%s",
                request_id,
            )
            raise DatabaseException("Failed to review correction request") from exc

    async def list_correction_request_logs(
        self,
        *,
        request_id: uuid.UUID,
        current_user: User,
    ) -> list[schemas.AttendanceCorrectionLogRead]:
        try:
            correction_request = (
                await self.correction_repo.get_correction_request_by_id(request_id)
            )
            if correction_request is None:
                raise NotFoundException("Correction request")

            await self.authorization_policy.ensure_can_view_employee(
                current_user,
                correction_request.employee_id,
            )

            logs = await self.correction_repo.list_correction_request_logs(request_id)
            return [
                schemas.AttendanceCorrectionLogRead.model_validate(log) for log in logs
            ]
        except AppException:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to list correction request logs: request_id=%s",
                request_id,
            )
            raise DatabaseException("Failed to list correction request logs") from exc


def get_correction_service(
    correction_repo: CorrectionRepo = Depends(get_correction_repo),
    authorization_policy: AuthorizationPolicy = Depends(get_authorization_policy),
) -> CorrectionService:
    return CorrectionService(correction_repo, authorization_policy)
