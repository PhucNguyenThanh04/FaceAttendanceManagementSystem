from __future__ import annotations

import binascii
import io
import os
import struct
import zipfile
from pathlib import Path

import pytest
from starlette.datastructures import Headers, UploadFile

from src.core.exceptions import (
    BadRequestException,
    PayloadTooLargeException,
    StorageQuotaExceededException,
)
from src.core.uploads.security import (
    atomic_write_with_quota,
    read_upload_limited,
    validate_document_upload,
    validate_image_upload,
)


def png_chunk(chunk_type: bytes, content: bytes) -> bytes:
    checksum = binascii.crc32(chunk_type + content) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(content))
        + chunk_type
        + content
        + struct.pack(">I", checksum)
    )


def valid_png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", b"")
        + png_chunk(b"IEND", b"")
    )


def valid_docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


def make_upload(content: bytes, *, filename: str, media_type: str) -> UploadFile:
    return UploadFile(
        io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": media_type}),
    )


@pytest.mark.asyncio
async def test_bounded_reader_returns_413_as_soon_as_limit_is_exceeded() -> None:
    upload = make_upload(b"123456", filename="data.txt", media_type="text/plain")

    with pytest.raises(PayloadTooLargeException) as exc_info:
        await read_upload_limited(upload, max_bytes=5, chunk_size=2)

    assert exc_info.value.status_code == 413


def test_document_rejects_extension_spoofing() -> None:
    with pytest.raises(BadRequestException, match="Invalid PDF"):
        validate_document_upload(
            filename="malware.pdf",
            declared_media_type="application/pdf",
            content=b"not a pdf",
        )


def test_docx_is_parsed_instead_of_trusting_its_mime_type() -> None:
    result = validate_document_upload(
        filename="policy.docx",
        declared_media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        content=valid_docx(),
    )

    assert result.extension == ".docx"


def test_image_rejects_mime_and_extension_mismatch() -> None:
    with pytest.raises(BadRequestException, match="do not match"):
        validate_image_upload(
            filename="avatar.png",
            declared_media_type="image/jpeg",
            content=valid_png(),
        )


def test_valid_png_is_checked_and_canonicalized() -> None:
    result = validate_image_upload(
        filename="avatar.png",
        declared_media_type="image/png",
        content=valid_png(),
    )

    assert result.media_type == "image/png"
    assert result.extension == ".png"


@pytest.mark.asyncio
async def test_atomic_write_enforces_directory_quota(tmp_path: Path) -> None:
    (tmp_path / "existing.bin").write_bytes(b"1234")

    with pytest.raises(StorageQuotaExceededException) as exc_info:
        await atomic_write_with_quota(
            storage_root=tmp_path,
            destination=tmp_path / "new.bin",
            content=b"567",
            quota_bytes=6,
        )

    assert exc_info.value.status_code == 507
    assert not (tmp_path / "new.bin").exists()
    assert not list(tmp_path.glob(".upload-*"))


@pytest.mark.asyncio
async def test_atomic_write_leaves_only_complete_destination(tmp_path: Path) -> None:
    destination = tmp_path / "avatar.png"

    await atomic_write_with_quota(
        storage_root=tmp_path,
        destination=destination,
        content=b"complete",
        quota_bytes=100,
    )

    assert destination.read_bytes() == b"complete"
    assert not list(tmp_path.glob(".upload-*"))


@pytest.mark.asyncio
async def test_interrupted_atomic_replace_leaves_no_partial_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "document.pdf"

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("simulated interrupted replace")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated interrupted replace"):
        await atomic_write_with_quota(
            storage_root=tmp_path,
            destination=destination,
            content=b"partial",
            quota_bytes=100,
        )

    assert not destination.exists()
    assert not list(tmp_path.glob(".upload-*"))
