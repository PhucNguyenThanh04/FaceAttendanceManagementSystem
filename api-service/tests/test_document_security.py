from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.features.documents.controller import router
from src.api.v1.features.documents.repository import DocumentRepository
from src.api.v1.features.documents.service import (
    DocumentService,
    get_document_service,
)
from src.api.v1.shared.enums import DocumentStatus, RoleName
from src.core.clients.chatbox.client import ChatboxClient
from src.core.dependencies.auth import get_current_user
from src.core.exception_handlers import register_exception_handlers
from src.core.exceptions import NotFoundException


class FakeDocumentRepository:
    def __init__(self, document=None) -> None:
        self.document = document

    async def get_document_or_404(self, document_id: uuid.UUID):
        if self.document is None or self.document.id != document_id:
            raise NotFoundException("Document")
        return self.document


class UnusedChatboxClient:
    pass


def make_service(document=None) -> DocumentService:
    return DocumentService(
        cast(DocumentRepository, FakeDocumentRepository(document)),
        cast(ChatboxClient, UnusedChatboxClient()),
    )


def make_document(*, filename: str, allowed_roles: list[str]):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(),
        title="Internal policy",
        file_name=filename,
        file_url=f"documents/{filename}",
        file_type=Path(filename).suffix.lstrip("."),
        uploaded_by=None,
        allowed_roles=allowed_roles,
        status=DocumentStatus.ready,
        chunk_count=1,
        qdrant_collection="documents",
        created_at=now,
        updated_at=now,
    )


def make_user(role: RoleName):
    return SimpleNamespace(role_name=role)


def make_app(service: DocumentService, user=None) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_document_service] = lambda: service
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


def test_download_requires_authentication() -> None:
    document = make_document(filename="policy.pdf", allowed_roles=["employee"])
    service = make_service(document)

    response = TestClient(make_app(service)).get(
        f"/api/v1/documents/{document.id}/download"
    )

    assert response.status_code == 401


def test_disallowed_role_cannot_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "src.api.v1.features.documents.service.UPLOAD_DIR",
        tmp_path,
    )
    document = make_document(filename="policy.pdf", allowed_roles=["hr"])
    (tmp_path / document.file_name).write_bytes(b"%PDF-1.7\n")
    service = make_service(document)

    response = TestClient(make_app(service, make_user(RoleName.employee))).get(
        f"/api/v1/documents/{document.id}/download"
    )

    assert response.status_code == 403


def test_allowed_role_can_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "src.api.v1.features.documents.service.UPLOAD_DIR",
        tmp_path,
    )
    document = make_document(filename="policy.pdf", allowed_roles=["employee"])
    expected = b"%PDF-1.7\ninternal"
    (tmp_path / document.file_name).write_bytes(expected)
    service = make_service(document)

    response = TestClient(make_app(service, make_user(RoleName.employee))).get(
        f"/api/v1/documents/{document.id}/download"
    )

    assert response.status_code == 200
    assert response.content == expected
    assert response.headers["cache-control"] == "private, no-store"


def test_missing_document_returns_404() -> None:
    missing_id = uuid.uuid4()
    service = make_service()

    response = TestClient(make_app(service, make_user(RoleName.admin))).get(
        f"/api/v1/documents/{missing_id}/download"
    )

    assert response.status_code == 404


def test_traversal_filename_cannot_escape_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.api.v1.features.documents.service.UPLOAD_DIR",
        tmp_path / "documents",
    )
    (tmp_path / "documents").mkdir()
    (tmp_path / "secret.pdf").write_bytes(b"secret")
    document = make_document(filename="../secret.pdf", allowed_roles=["admin"])
    service = make_service(document)

    response = TestClient(make_app(service, make_user(RoleName.admin))).get(
        f"/api/v1/documents/{document.id}/download"
    )

    assert response.status_code == 404


def test_old_static_document_url_is_not_registered() -> None:
    document = make_document(filename="policy.pdf", allowed_roles=["employee"])
    service = make_service(document)

    response = TestClient(make_app(service, make_user(RoleName.employee))).get(
        f"/uploads/documents/{document.file_name}"
    )

    assert response.status_code == 404


def test_document_response_exposes_only_protected_download_url() -> None:
    document = make_document(filename="policy.pdf", allowed_roles=["employee"])
    service = make_service(document)

    response = service._to_read(document)

    assert response.file_url == f"/api/v1/documents/{document.id}/download"
    assert "/uploads/documents/" not in response.file_url
