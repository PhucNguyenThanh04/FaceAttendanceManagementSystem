from fastapi import APIRouter

from app.api.v1.features.attendance.controller import router as attendance_router
from app.api.v1.features.register.controller import router as register_router

api_router = APIRouter()
api_router.include_router(attendance_router)
api_router.include_router(register_router)
