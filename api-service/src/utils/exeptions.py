# app/core/exceptions.py

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """
    Base exception cho toàn bộ custom exception của app.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "APP_ERROR",
        detail: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail or {}


class BadRequestException(AppException):
    """
    Request sai logic hoặc dữ liệu không hợp lệ ở mức business.
    """

    def __init__(
        self,
        message: str = "Bad request",
        detail: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="BAD_REQUEST",
            detail=detail,
        )


class ValidationException(AppException):
    """
    Dữ liệu input không hợp lệ.
    """

    def __init__(
        self,
        message: str = "Validation error",
        detail: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            detail=detail,
        )


class UnauthorizedException(AppException):
    """
    Chưa đăng nhập hoặc token không hợp lệ.
    """

    def __init__(
        self,
        message: str = "Unauthorized",
        detail: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED",
            detail=detail,
        )


class ForbiddenException(AppException):
    """
    Đã đăng nhập nhưng không có quyền.
    """

    def __init__(
        self,
        message: str = "Forbidden",
        detail: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
            detail=detail,
        )


class NotFoundException(AppException):
    """
    Không tìm thấy resource.
    """

    def __init__(
        self,
        resource: str = "Resource",
        detail: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=f"{resource} not found",
            status_code=404,
            error_code="NOT_FOUND",
            detail=detail,
        )


class ConflictException(AppException):
    """
    Dữ liệu bị trùng hoặc xung đột trạng thái.
    Ví dụ: email đã tồn tại, đã check-in hôm nay.
    """

    def __init__(
        self,
        message: str = "Conflict",
        detail: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            detail=detail,
        )


class InternalServerException(AppException):
    """
    Lỗi hệ thống không mong muốn.
    """

    def __init__(
        self,
        message: str = "Internal server error",
        detail: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="INTERNAL_SERVER_ERROR",
            detail=detail,
        )


class DatabaseException(AppException):
    """
    Lỗi thao tác database.
    Không nên trả raw SQL/database error ra ngoài.
    """

    def __init__(
        self,
        message: str = "Database operation failed",
        detail: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            detail=detail,
        )


class MLProcessingException(AppException):
    """
    Lỗi xử lý AI/ML pipeline.
    Dùng cho ai-service hoặc các flow gọi sang ai-service.
    """

    def __init__(
        self,
        step: str,
        reason: str,
        task_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ):
        message = f"ML step '{step}' failed: {reason}"

        if task_id:
            message = f"[task={task_id}] {message}"

        super().__init__(
            message=message,
            status_code=500,
            error_code="ML_PROCESSING_ERROR",
            detail=detail,
        )

        self.task_id = task_id


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """
    Handler cho toàn bộ AppException.
    Đăng ký trong main.py bằng app.add_exception_handler(...)
    """

    if exc.status_code >= 500:
        logger.error(
            "App exception occurred: %s",
            exc.message,
            exc_info=True,
        )
    else:
        logger.warning(
            "App exception occurred: %s",
            exc.message,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code,
            "detail": exc.detail,
            "path": request.url.path,
        },
    )