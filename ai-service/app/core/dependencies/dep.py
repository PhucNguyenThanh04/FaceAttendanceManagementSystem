from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from app.core.configs.settings import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")


def get_register_service(request: Request):
    return request.app.state.register_service
#
#
# def get_attendance_service(request: Request):
#     return request.app.state.attendance_service
#
#
# def get_camera_service(request: Request):
#     return request.app.state.camera_service
