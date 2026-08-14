import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from src.api.v1.features.users.models import User
from src.core.configs.settings import settings
from src.core.dependencies.auth import get_current_user
from src.core.uploads.security import (
    atomic_write_with_quota,
    read_upload_limited,
    validate_image_upload,
)

router = APIRouter(prefix="/upload", tags=["Upload"])

BASE_DIR = Path(__file__).resolve().parents[5]
UPLOAD_DIR = BASE_DIR / "uploads" / "avatars"
MAX_FILE_SIZE = settings.avatar_upload_max_bytes
AVATAR_STORAGE_QUOTA = settings.avatar_storage_quota_bytes


async def _save_avatar_image(file: UploadFile) -> dict[str, str]:
    content = await read_upload_limited(
        file,
        max_bytes=MAX_FILE_SIZE,
        chunk_size=settings.upload_chunk_size_bytes,
    )
    validated_upload = validate_image_upload(
        filename=file.filename or "",
        declared_media_type=file.content_type,
        content=content,
    )
    filename = f"{uuid.uuid4()}{validated_upload.extension}"
    file_path = UPLOAD_DIR / filename
    await atomic_write_with_quota(
        storage_root=UPLOAD_DIR,
        destination=file_path,
        content=validated_upload.content,
        quota_bytes=AVATAR_STORAGE_QUOTA,
    )

    return {
        "image_url": f"/uploads/avatars/{filename}",
        "filename": filename,
    }


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> dict[str, str]:
    return await _save_avatar_image(file)


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> dict[str, str]:
    return await _save_avatar_image(file)
