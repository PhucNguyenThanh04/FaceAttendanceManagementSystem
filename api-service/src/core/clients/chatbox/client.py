from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from src.core.clients.chatbox.schemas import (
    ChatboxPaths,
    ChatRequest,
    ChatResponse,
    DocumentIngestResponse,
    DocumentVectorDeleteResponse,
)
from src.core.configs.settings import settings
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class ChatboxClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client
        self._api_key = settings.rag_api_key
        self._default_headers = {"X-API-Key": self._api_key} if self._api_key else {}

    async def chat(self, request: ChatRequest) -> ChatResponse:
        data = await self._request_json(
            method="POST",
            path=ChatboxPaths.CHAT_MESSAGE,
            json=request.model_dump(mode="json"),
        )
        return ChatResponse.model_validate(data)

    async def ingest_document(
        self,
        *,
        document_id: str,
        filename: str,
        file_path: str,
        allowed_roles: list[str],
        file_bytes: bytes,
        upload_filename: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> DocumentIngestResponse:
        normalized_document_id = document_id.strip()
        normalized_filename = filename.strip()
        normalized_file_path = file_path.strip()
        if not normalized_document_id:
            raise ValueError("document_id must not be empty")
        if not normalized_filename:
            raise ValueError("filename must not be empty")
        if not normalized_file_path:
            raise ValueError("file_path must not be empty")
        if not allowed_roles:
            raise ValueError("allowed_roles must not be empty")
        normalized_allowed_roles = [role.strip() for role in allowed_roles if role.strip()]
        if not normalized_allowed_roles:
            raise ValueError("allowed_roles must not be empty")
        if not file_bytes:
            raise ValueError("file_bytes must not be empty")

        form_data = [
            ("document_id", normalized_document_id),
            ("filename", normalized_filename),
            ("file_path", normalized_file_path),
            *[("allowed_roles", role) for role in normalized_allowed_roles],
        ]
        data = await self._request_json(
            method="POST",
            path=ChatboxPaths.DOCUMENTS,
            data=form_data,
            files={
                "file": (
                    upload_filename or normalized_filename,
                    file_bytes,
                    content_type,
                )
            },
        )
        return DocumentIngestResponse.model_validate(data)

    async def delete_document_vectors(
        self,
        document_id: str,
    ) -> DocumentVectorDeleteResponse:
        normalized_document_id = document_id.strip()
        if not normalized_document_id:
            raise ValueError("document_id must not be empty")

        safe_document_id = quote(normalized_document_id, safe="")
        data = await self._request_json(
            method="DELETE",
            path=ChatboxPaths.DOCUMENT_VECTORS.format(
                document_id=safe_document_id,
            ),
        )
        return DocumentVectorDeleteResponse.model_validate(data)

    async def _request_json(
        self,
        *,
        method: str,
        path: str,
        require_api_key: bool = True,
        **kwargs: Any,
    ) -> Any:
        headers = dict(kwargs.pop("headers", {}))
        if require_api_key:
            headers.update(self._default_headers)

        response = await self._http.request(method, path, headers=headers, **kwargs)
        response.raise_for_status()
        logger.debug(
            "HTTP %s %s | status=%s | response=%s",
            method,
            path,
            response.status_code,
            response.text,
        )
        return response.json()


def get_chatbox_client(http_client: httpx.AsyncClient) -> ChatboxClient:
    return ChatboxClient(http_client)
