from __future__ import annotations

import asyncio
import binascii
import fcntl
import io
import os
import struct
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from fastapi import UploadFile

from src.core.exceptions import (
    BadRequestException,
    PayloadTooLargeException,
    StorageQuotaExceededException,
)

MAX_IMAGE_PIXELS = 25_000_000
MAX_DOCX_ENTRIES = 10_000
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024

DOCUMENT_MEDIA_TYPES = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
    ".txt": {"text/plain", "application/octet-stream"},
}
IMAGE_MEDIA_TYPES = {
    ".jpg": {"image/jpeg", "image/jpg", "application/octet-stream"},
    ".png": {"image/png", "application/octet-stream"},
}


@dataclass(frozen=True)
class ValidatedUpload:
    content: bytes
    extension: str
    media_type: str


async def read_upload_limited(
    upload: UploadFile,
    *,
    max_bytes: int,
    chunk_size: int,
) -> bytes:
    """Read an upload incrementally and stop as soon as its bound is exceeded."""
    if max_bytes <= 0 or chunk_size <= 0:
        raise RuntimeError("upload limits must be positive")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(min(chunk_size, max_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLargeException(
                f"File exceeds the {max_bytes}-byte upload limit",
                detail={"max_bytes": max_bytes},
            )
        chunks.append(chunk)
    return b"".join(chunks)


def validate_document_upload(
    *,
    filename: str,
    declared_media_type: str | None,
    content: bytes,
) -> ValidatedUpload:
    extension = Path(filename).suffix.lower()
    if extension not in DOCUMENT_MEDIA_TYPES:
        raise BadRequestException("Only PDF, DOCX and UTF-8 TXT files are allowed")
    _validate_declared_media_type(
        extension=extension,
        declared_media_type=declared_media_type,
        allowed=DOCUMENT_MEDIA_TYPES,
    )
    if not content:
        raise BadRequestException("Empty file is not allowed")

    if extension == ".pdf":
        _validate_pdf(content)
        media_type = "application/pdf"
    elif extension == ".docx":
        _validate_docx(content)
        media_type = (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
    else:
        _validate_text(content)
        media_type = "text/plain"

    return ValidatedUpload(content=content, extension=extension, media_type=media_type)


def validate_image_upload(
    *,
    filename: str,
    declared_media_type: str | None,
    content: bytes,
) -> ValidatedUpload:
    extension = Path(filename).suffix.lower()
    if extension == ".jpeg":
        extension = ".jpg"
    if extension not in IMAGE_MEDIA_TYPES:
        raise BadRequestException("Only JPG and PNG images are allowed")
    _validate_declared_media_type(
        extension=extension,
        declared_media_type=declared_media_type,
        allowed=IMAGE_MEDIA_TYPES,
    )
    if not content:
        raise BadRequestException("Empty file is not allowed")

    if extension == ".png":
        _validate_png(content)
        media_type = "image/png"
    else:
        _validate_jpeg(content)
        media_type = "image/jpeg"
    return ValidatedUpload(content=content, extension=extension, media_type=media_type)


async def atomic_write_with_quota(
    *,
    storage_root: Path,
    destination: Path,
    content: bytes,
    quota_bytes: int,
) -> None:
    await asyncio.to_thread(
        _atomic_write_with_quota_sync,
        storage_root,
        destination,
        content,
        quota_bytes,
    )


def _validate_declared_media_type(
    *,
    extension: str,
    declared_media_type: str | None,
    allowed: dict[str, set[str]],
) -> None:
    normalized = (declared_media_type or "application/octet-stream").split(";", 1)[
        0
    ].strip().lower()
    if normalized not in allowed[extension]:
        raise BadRequestException("File extension and media type do not match")


def _validate_pdf(content: bytes) -> None:
    if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
        raise BadRequestException("Invalid PDF file")


def _validate_docx(content: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            names = {entry.filename for entry in entries}
            if len(entries) > MAX_DOCX_ENTRIES:
                raise BadRequestException("DOCX contains too many entries")
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise BadRequestException("Invalid DOCX structure")

            uncompressed_size = 0
            for entry in entries:
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or ".." in path.parts:
                    raise BadRequestException("Unsafe DOCX entry path")
                if entry.flag_bits & 0x1:
                    raise BadRequestException("Encrypted DOCX files are not allowed")
                uncompressed_size += entry.file_size
                if uncompressed_size > MAX_DOCX_UNCOMPRESSED_BYTES:
                    raise BadRequestException("DOCX expands beyond the safe limit")

            archive.read("[Content_Types].xml")
            archive.read("word/document.xml")
    except (zipfile.BadZipFile, RuntimeError, KeyError) as exc:
        raise BadRequestException("Invalid DOCX file") from exc


def _validate_text(content: bytes) -> None:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BadRequestException("TXT files must be valid UTF-8") from exc
    if "\x00" in text:
        raise BadRequestException("TXT files must not contain NUL bytes")


def _validate_png(content: bytes) -> None:
    signature = b"\x89PNG\r\n\x1a\n"
    if not content.startswith(signature):
        raise BadRequestException("Invalid PNG file")

    offset = len(signature)
    saw_ihdr = False
    saw_iend = False
    while offset + 12 <= len(content):
        length = struct.unpack(">I", content[offset : offset + 4])[0]
        chunk_type = content[offset + 4 : offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(content):
            raise BadRequestException("Truncated PNG file")
        expected_crc = struct.unpack(">I", content[data_end:crc_end])[0]
        actual_crc = binascii.crc32(chunk_type + content[data_start:data_end]) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise BadRequestException("Invalid PNG checksum")

        if not saw_ihdr:
            if chunk_type != b"IHDR" or length != 13:
                raise BadRequestException("Invalid PNG header")
            width, height = struct.unpack(">II", content[data_start : data_start + 8])
            _validate_image_dimensions(width, height)
            saw_ihdr = True
        if chunk_type == b"IEND":
            if length != 0 or crc_end != len(content):
                raise BadRequestException("Invalid PNG ending")
            saw_iend = True
            break
        offset = crc_end

    if not saw_ihdr or not saw_iend:
        raise BadRequestException("Invalid PNG file")


def _validate_jpeg(content: bytes) -> None:
    if len(content) < 4 or not content.startswith(b"\xff\xd8") or not content.endswith(
        b"\xff\xd9"
    ):
        raise BadRequestException("Invalid JPEG file")

    offset = 2
    found_dimensions = False
    start_of_frame_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while offset < len(content) - 2:
        if content[offset] != 0xFF:
            raise BadRequestException("Invalid JPEG marker")
        while offset < len(content) and content[offset] == 0xFF:
            offset += 1
        if offset >= len(content):
            break
        marker = content[offset]
        offset += 1
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if marker == 0xDA:
            break
        if offset + 2 > len(content):
            raise BadRequestException("Truncated JPEG file")
        segment_length = struct.unpack(">H", content[offset : offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(content):
            raise BadRequestException("Invalid JPEG segment")
        if marker in start_of_frame_markers:
            if segment_length < 7:
                raise BadRequestException("Invalid JPEG dimensions")
            height, width = struct.unpack(">HH", content[offset + 3 : offset + 7])
            _validate_image_dimensions(width, height)
            found_dimensions = True
        offset += segment_length

    if not found_dimensions:
        raise BadRequestException("JPEG dimensions are missing")


def _validate_image_dimensions(width: int, height: int) -> None:
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise BadRequestException("Image dimensions exceed the safe limit")


def _atomic_write_with_quota_sync(
    storage_root: Path,
    destination: Path,
    content: bytes,
    quota_bytes: int,
) -> None:
    if quota_bytes <= 0:
        raise RuntimeError("storage quota must be positive")

    storage_root.mkdir(parents=True, exist_ok=True)
    root = storage_root.resolve()
    target = destination.resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("upload destination escapes its storage root") from exc
    if target.parent != root:
        raise RuntimeError("nested upload destinations are not supported")

    lock_path = root / ".upload.lock"
    temp_path: Path | None = None
    with lock_path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        existing_size = sum(
            item.stat().st_size
            for item in root.iterdir()
            if item.is_file()
            and not item.is_symlink()
            and item.name != lock_path.name
            and item != target
        )
        projected_size = existing_size + len(content)
        if projected_size > quota_bytes:
            raise StorageQuotaExceededException(
                detail={
                    "quota_bytes": quota_bytes,
                    "projected_bytes": projected_size,
                }
            )

        descriptor, temp_name = tempfile.mkstemp(prefix=".upload-", dir=root)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "wb") as temp_file:
                temp_file.write(content)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, target)
            temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
