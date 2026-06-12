from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.features.documents.schemas import DocumentIngestResponse


router = APIRouter(prefix="/api/v1", tags=["Documents"])

@router.post("/rag/documents", response_model=DocumentIngestResponse)
async def upload_document(file: UploadFile = File(...), collection: str = Form(...)):
    ... 
