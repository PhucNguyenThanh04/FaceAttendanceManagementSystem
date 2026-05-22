
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("uvicorn.access")


class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        logger.info(f"[REQ] {request.method} {request.url}")
        try:
            response = await call_next(request)
        except Exception as e:
            logger.exception(f"[ERROR] {request.method} {request.url} failed")
            return JSONResponse({"error": "Internal server error"}, status_code=500)
        logger.info(f"[RES] {request.method} {request.url} status {response.status_code}")
        return response
