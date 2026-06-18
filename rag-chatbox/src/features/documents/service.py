from fastapi import UploadFile, HTTPException, File, Form, Depends
from dataclasses import dataclass
from typing import Any

from src.rag.ingestion.pipeline import IngestionPipeline
from src.core.dependenci import get_ingestion_pipeline
from src.features.documents.schemas import DocumentIngestResponse

from src.core.setup_logging import setup_logger

logger = setup_logger(__name__)

class DocumentService:
    def __init__(self,
        ingestion_pipeline: IngestionPipeline,
    ) -> None:
        self.ingestion_pipeline = ingestion_pipeline

    async def ingestion(self,
        file: UploadFile,
        document_id: str,
        filename: str,
        file_path: str,
        allowed_roles: list[Any],
    ) -> DocumentIngestResponse:
        try:
            result = await self.ingestion_pipeline.ingestion(
                file=file,
                document_id=document_id,
                filename=filename,
                file_path=file_path,
                allowed_roles=allowed_roles,
            )
        except ValueError as exc:
            logger.error(f"Ingestion failed for document {document_id}: {exc}")
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.error(f"Unexpected error during ingestion of document {document_id}: {exc}")
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return DocumentIngestResponse(
            document_id=result.document_id,
            filename=result.filename,
            collection=result.collection,
            status=result.status,
            chunks_count=result.chunks_count,
            vector_indexed=result.vector_indexed,
            keyword_indexed=result.keyword_indexed,
            error_code=result.error_code,
            message=result.message,
        )



def get_document_service(ingestion_pipeline: IngestionPipeline = Depends(get_ingestion_pipeline)) -> DocumentService:
    return DocumentService(
        ingestion_pipeline=ingestion_pipeline,
    )
