from __future__ import annotations

import cv2
import numpy as np
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.core.dependencies.dep import verify_api_key
from app.api.v1.features.register.service import RegisterService, get_register_service
from app.api.v1.features.register import schemas as schemas_register
from app.core.vector_db import schemas as schemas_vector


router = APIRouter(
    prefix="/faces",
    tags=["register"],
    dependencies=[Depends(verify_api_key)],
)


def _decode_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Không thể đọc ảnh — kiểm tra định dạng file.")
    return img


@router.post("/enroll/photo", response_model=schemas_register.AddPhotoResponse)
async def add_photo(
    session_id: str,
    file: UploadFile = File(...),
    service: RegisterService = Depends(get_register_service),
):
    image = _decode_image(await file.read())
    return await service.add_photo(session_id, image)


@router.post("/enroll/commit", response_model=schemas_register.CommitResponse)
async def commit(
    body: schemas_register.CommitRequest,   # session_id + payload (PayloadCreateRequest)
    service: RegisterService = Depends(get_register_service),

):
    try:
        return await service.commit(body.session_id, body.payload)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/enroll/re-enroll", response_model=schemas_register.CommitResponse)
async def re_enroll(
    body: schemas_register.CommitRequest,   # dùng cùng schema với commit
    service: RegisterService = Depends(get_register_service),
):
    try:
        return await service.re_enroll(body.session_id, body.payload)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/enroll/{session_id}")
async def cancel_enrollment(
    session_id: str,
    service: RegisterService = Depends(get_register_service),
):
    await service.cancel(session_id)
    return {"cancelled": True, "session_id": session_id}


@router.delete("/{staff_id}")
async def delete_person(
    staff_id: str,
    service: RegisterService = Depends(get_register_service),
):
    deleted = await service.delete_person(staff_id)
    return {"deleted": True, "staff_id": staff_id, "vectors_removed": deleted}


@router.patch("/{staff_id}/deactivate")
async def deactivate_person(
    staff_id: str,
    service: RegisterService = Depends(get_register_service),
):
    updated = await service.deactivate_person(staff_id)
    return {
        "deactivated": True,
        "staff_id": staff_id,
        "vectors_updated": updated,
        "is_active": False,
    }


@router.patch("/{staff_id}/activate")
async def activate_person(
    staff_id: str,
    service: RegisterService = Depends(get_register_service),
):
    updated = await service.activate_person(staff_id)
    return {
        "activated": True,
        "staff_id": staff_id,
        "vectors_updated": updated,
        "is_active": True,
    }


@router.get("/{staff_id}/status")
async def check_enrolled(
    staff_id: str,
    service: RegisterService = Depends(get_register_service),
):
    count = await service.count_vectors(staff_id)
    return {"enrolled": count > 0, "vector_count": count, "staff_id": staff_id}
