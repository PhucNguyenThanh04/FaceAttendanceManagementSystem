import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status

from src.api.v1.features.employee_onboarding import schemas
from src.api.v1.features.employee_onboarding.service import (
    EmployeeOnboardingService,
    get_employee_onboarding_service,
)
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import RoleName
from src.core.configs.settings import settings
from src.core.dependencies.auth import require_roles
from src.core.uploads.security import read_upload_limited, validate_image_upload

router = APIRouter(prefix="/employee-onboarding", tags=["Employee Onboarding"])


@router.post(
    "/start-session",
    response_model=schemas.EmployeeOnboardingStartSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_onboarding_session(
    payload: schemas.EmployeeOnboardingStartSessionRequest,
    service: EmployeeOnboardingService = Depends(get_employee_onboarding_service),
    current_user: User = Depends(require_roles(RoleName.admin, RoleName.hr)),
) -> schemas.EmployeeOnboardingStartSessionResponse:
    return await service.start_onboarding_session(
        payload=payload,
        created_by=current_user.user_id,
    )


@router.post(
    "/{session_id}/images",
    response_model=schemas.EmployeeOnboardingPhotoUploadResponse,
)
async def upload_onboarding_image(
    session_id: str,
    file: UploadFile = File(...),
    service: EmployeeOnboardingService = Depends(get_employee_onboarding_service),
    _: User = Depends(require_roles(RoleName.admin, RoleName.hr)),
) -> schemas.EmployeeOnboardingPhotoUploadResponse:
    image_bytes = await read_upload_limited(
        file,
        max_bytes=settings.onboarding_image_max_bytes,
        chunk_size=settings.upload_chunk_size_bytes,
    )
    validated_upload = validate_image_upload(
        filename=file.filename or "",
        declared_media_type=file.content_type,
        content=image_bytes,
    )

    return await service.upload_photo_to_session(
        session_id=session_id,
        image_bytes=validated_upload.content,
        filename=f"{uuid.uuid4()}{validated_upload.extension}",
        content_type=validated_upload.media_type,
    )


@router.post(
    "/commit",
    response_model=schemas.EmployeeOnboardingCommitResponse,
)
async def commit_onboarding_session(
    payload: schemas.EmployeeOnboardingCommitRequest,
    service: EmployeeOnboardingService = Depends(get_employee_onboarding_service),
    _: User = Depends(require_roles(RoleName.admin, RoleName.hr)),
) -> schemas.EmployeeOnboardingCommitResponse:
    return await service.commit_onboarding_session(payload.session_id)


@router.post(
    "/{session_id}/cancel",
    response_model=schemas.EmployeeOnboardingCancelResponse,
)
async def cancel_onboarding_session(
    session_id: str,
    service: EmployeeOnboardingService = Depends(get_employee_onboarding_service),
    current_user: User = Depends(require_roles(RoleName.admin, RoleName.hr)),
) -> schemas.EmployeeOnboardingCancelResponse:
    return await service.cancel_onboarding_session(
        session_id=session_id,
        cancelled_by=current_user.user_id,
    )
