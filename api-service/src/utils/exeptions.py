
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class AppBaseException(Exception):
    """Base exception for all custom app errors."""
    def __init__(self, message: str, code: int = 400, detail: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.detail = detail or {}


class NotFoundException(AppBaseException):
    """Resource not found"""
    def __init__(self, resource: str):
        super().__init__(f"{resource} not found", code=404)

class ValidationException(AppBaseException):
    """Invalid input"""
    def __init__(self, field: str, reason: str):
        super().__init__(f"Invalid {field}: {reason}", code=422)

class AuthException(AppBaseException):
    """Authentication / Authorization failure"""
    def __init__(self, message="Unauthorized"):
        super().__init__(message, code=401)

class MLProcessingException(AppBaseException):
    """ML pipeline failed"""
    def __init__(self, step: str, reason: str, task_id: str = None):
        msg = f"ML step '{step}' failed: {reason}"
        if task_id:
            msg = f"[task={task_id}] {msg}"
        super().__init__(msg, code=500)
        self.task_id = task_id

class DatabaseException(AppBaseException):
    """Database error"""
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(detail, code=500)


async def app_exception_handler(request: Request, exc: AppBaseException):
    # Log traceback if available
    logger.exception(f"Exception occurred: {exc.message}")
    return JSONResponse(
        status_code=exc.code,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "path": str(request.url)
        }
    )

# from fastapi import FastAPI
# from utils.exceptions import app_exception_handler, AppBaseException
#
# app = FastAPI()
# app.add_exception_handler(AppBaseException, app_exception_handler)
#
# # Example endpoint
# @app.get("/staff/{staff_id}")
# async def get_staff(staff_id: str):
#     raise NotFoundException("Staff")