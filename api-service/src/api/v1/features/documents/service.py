from __future__ import annotations

import mimetypes
import re
import uuid
from pathlib import Path

import httpx
from fastapi import Depends, UploadFile

from src.api.v1.features.documents import schemas
from src.api.v1.features.documents.models import Document
from src.api.v1.features.documents.repository import (
    DocumentRepository,
    get_document_repository,
)
from src.api.v1.features.staff.models import Employee
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import RoleName
from src.core.clients.chatbox.client import ChatboxClient
from src.core.configs.settings import settings
from src.core.dependencies.dep import get_chatbox_http_client
from src.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    MLProcessingException,
    NotFoundException,
)
from src.core.uploads.security import (
    atomic_write_with_quota,
    read_upload_limited,
    validate_document_upload,
)
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)

BASE_DIR = Path(__file__).resolve().parents[5]
UPLOAD_DIR = BASE_DIR / "uploads" / "documents"
PROTECTED_DOWNLOAD_PREFIX = "/api/v1/documents"
MAX_DOCUMENT_SIZE = settings.document_upload_max_bytes
DOCUMENT_STORAGE_QUOTA = settings.document_storage_quota_bytes
PENDING_QDRANT_COLLECTION = "pending"
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


class DocumentService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        chatbox_client: ChatboxClient,
    ) -> None:
        self.document_repository = document_repository
        self.chatbox_client = chatbox_client

    @staticmethod
    def _to_read(document: Document) -> schemas.DocumentRead:
        response = schemas.DocumentRead.model_validate(document)
        return response.model_copy(
            update={"file_url": (f"{PROTECTED_DOWNLOAD_PREFIX}/{document.id}/download")}
        )

    @staticmethod
    def _storage_key(filename: str) -> str:
        return f"documents/{filename}"

    @staticmethod
    def _resolve_document_path(filename: str) -> Path:
        """Resolve a stored filename without allowing traversal or symlink escape."""
        if not filename or Path(filename).name != filename:
            raise NotFoundException("Document file")

        storage_root = UPLOAD_DIR.resolve()
        candidate = (storage_root / filename).resolve()
        try:
            candidate.relative_to(storage_root)
        except ValueError as exc:
            raise NotFoundException("Document file") from exc

        if not candidate.is_file():
            raise NotFoundException("Document file")
        return candidate

    @staticmethod
    def _role_can_download(document: Document, current_user: User) -> bool:
        if current_user.role_name == RoleName.admin:
            return True
        allowed_roles = {
            role.strip().lower()
            for role in document.allowed_roles
            if role and role.strip()
        }
        return current_user.role_name.value in allowed_roles

    @staticmethod
    def _safe_filename(filename: str) -> str:
        basename = Path(filename).name.strip()
        if not basename:
            raise BadRequestException("filename is required")
        stem = Path(basename).stem.strip() or "document"
        suffix = Path(basename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise BadRequestException(
                f"Unsupported file type. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._")
        return f"{safe_stem or 'document'}{suffix}"

    @staticmethod
    def _normalize_allowed_roles(allowed_roles: list[str]) -> list[str]:
        normalized = [
            role.strip()
            for item in allowed_roles
            for role in item.split(",")
            if role.strip()
        ]
        if not normalized:
            raise BadRequestException("allowed_roles is required")
        if len(normalized) != len(set(normalized)):
            raise BadRequestException("allowed_roles must not contain duplicates")
        return normalized

    @staticmethod
    def _delete_local_file(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            logger.warning(
                "Failed to delete local document file: path=%s", path, exc_info=True
            )

    async def upload_document(
        self,
        *,
        title: str,
        allowed_roles: list[str],
        file: UploadFile,
        current_employee: Employee,
    ) -> schemas.DocumentRead:
        normalized_title = title.strip()
        if not normalized_title:
            raise BadRequestException("title is required")

        normalized_allowed_roles = self._normalize_allowed_roles(allowed_roles)
        safe_original_filename = self._safe_filename(file.filename or "")
        file_bytes = await read_upload_limited(
            file,
            max_bytes=MAX_DOCUMENT_SIZE,
            chunk_size=settings.upload_chunk_size_bytes,
        )
        validated_upload = validate_document_upload(
            filename=safe_original_filename,
            declared_media_type=file.content_type,
            content=file_bytes,
        )

        document_id = uuid.uuid4()
        stored_filename = f"{document_id}{validated_upload.extension}"
        local_path = UPLOAD_DIR / stored_filename
        storage_key = self._storage_key(stored_filename)
        file_type = validated_upload.extension.lstrip(".")

        await atomic_write_with_quota(
            storage_root=UPLOAD_DIR,
            destination=local_path,
            content=validated_upload.content,
            quota_bytes=DOCUMENT_STORAGE_QUOTA,
        )

        document_created = False
        rag_cleanup_needed = False
        try:
            await self.document_repository.create_processing_document(
                document_id=document_id,
                title=normalized_title,
                file_name=stored_filename,
                file_url=storage_key,
                file_type=file_type,
                uploaded_by=current_employee.employee_id,
                allowed_roles=normalized_allowed_roles,
                qdrant_collection=PENDING_QDRANT_COLLECTION,
            )
            document_created = True

            rag_cleanup_needed = True
            ingest_result = await self.chatbox_client.ingest_document(
                document_id=str(document_id),
                filename=stored_filename,
                file_path=storage_key,
                allowed_roles=normalized_allowed_roles,
                file_bytes=validated_upload.content,
                upload_filename=stored_filename,
                content_type=validated_upload.media_type,
            )

            document = await self.document_repository.mark_ready(
                document_id=document_id,
                chunk_count=ingest_result.chunks_count,
                qdrant_collection=ingest_result.collection,
            )
            return self._to_read(document)
        except (httpx.HTTPError, ValueError) as exc:
            if rag_cleanup_needed:
                await self._cleanup_document_vectors(document_id)
            if document_created:
                await self._cleanup_document_record(document_id)
            self._delete_local_file(local_path)
            raise MLProcessingException(
                step="rag_document_ingest",
                reason=str(exc),
                task_id=str(document_id),
            ) from exc
        except Exception:
            if rag_cleanup_needed:
                await self._cleanup_document_vectors(document_id)
            if document_created:
                await self._cleanup_document_record(document_id)
            self._delete_local_file(local_path)
            raise

    async def _cleanup_document_record(self, document_id: uuid.UUID) -> None:
        try:
            await self.document_repository.delete_document(document_id)
        except Exception:
            logger.warning(
                "Failed to cleanup document record: document_id=%s",
                document_id,
                exc_info=True,
            )

    async def _cleanup_document_vectors(self, document_id: uuid.UUID) -> None:
        try:
            await self.chatbox_client.delete_document_vectors(str(document_id))
        except Exception:
            logger.warning(
                "Failed to cleanup document vectors: document_id=%s",
                document_id,
                exc_info=True,
            )

    async def get_document(self, document_id: uuid.UUID) -> schemas.DocumentRead:
        document = await self.document_repository.get_document_or_404(document_id)
        return self._to_read(document)

    async def get_document_download(
        self,
        *,
        document_id: uuid.UUID,
        current_user: User,
    ) -> tuple[Path, str, str]:
        document = await self.document_repository.get_document_or_404(document_id)
        if not self._role_can_download(document, current_user):
            raise ForbiddenException("You do not have access to this document")

        local_path = self._resolve_document_path(document.file_name)
        media_type = mimetypes.guess_type(document.file_name)[0]
        return (
            local_path,
            Path(document.file_name).name,
            media_type or "application/octet-stream",
        )

    async def list_documents(self, query: schemas.DocumentListQuery) -> dict:
        documents, total = await self.document_repository.list_documents(query)
        return {
            "items": [self._to_read(document) for document in documents],
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
        }

    async def update_document(
        self,
        document_id: uuid.UUID,
        payload: schemas.DocumentUpdate,
    ) -> schemas.DocumentRead:
        document = await self.document_repository.get_document_or_404(document_id)

        if (
            payload.allowed_roles is not None
            and payload.allowed_roles != document.allowed_roles
        ):
            local_path = self._resolve_document_path(document.file_name)

            try:
                ingest_result = await self.chatbox_client.ingest_document(
                    document_id=str(document.id),
                    filename=document.file_name,
                    file_path=self._storage_key(document.file_name),
                    allowed_roles=payload.allowed_roles,
                    file_bytes=local_path.read_bytes(),
                    upload_filename=document.file_name,
                    content_type="application/octet-stream",
                )
                if ingest_result.status != "ready" or not ingest_result.vector_indexed:
                    raise ValueError(
                        ingest_result.message
                        or "RAG did not finish updating document metadata"
                    )
            except (httpx.HTTPError, ValueError) as exc:
                logger.exception(
                    "Failed to update document vector metadata: document_id=%s",
                    document_id,
                )
                raise MLProcessingException(
                    step="rag_document_metadata_update",
                    reason=str(exc),
                    task_id=str(document_id),
                ) from exc

        updated = await self.document_repository.update_document(document, payload)
        logger.info("Document metadata updated: document_id=%s", document_id)
        return self._to_read(updated)

    async def delete_document(self, document_id: uuid.UUID) -> None:
        document = await self.document_repository.get_document_or_404(document_id)
        try:
            await self.chatbox_client.delete_document_vectors(str(document_id))
        except (httpx.HTTPError, ValueError) as exc:
            logger.exception(
                "Failed to delete document vectors: document_id=%s", document_id
            )
            raise MLProcessingException(
                step="rag_document_delete",
                reason=str(exc),
                task_id=str(document_id),
            ) from exc

        await self.document_repository.delete_document(document_id)
        try:
            local_path = self._resolve_document_path(document.file_name)
        except NotFoundException:
            logger.warning(
                "Document record deleted but local file was missing or unsafe: document_id=%s",
                document_id,
            )
        else:
            self._delete_local_file(local_path)


def get_document_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
    chatbox_http_client: httpx.AsyncClient = Depends(get_chatbox_http_client),
) -> DocumentService:
    return DocumentService(
        document_repository=document_repository,
        chatbox_client=ChatboxClient(chatbox_http_client),
    )
