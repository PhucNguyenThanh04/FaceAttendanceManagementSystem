from fastapi import APIRouter
from src.api.v1.document_router import router as document_router

router = APIRouter()
router.include_router(document_router)