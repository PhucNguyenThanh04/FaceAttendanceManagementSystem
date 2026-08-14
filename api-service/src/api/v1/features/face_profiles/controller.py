from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from src.api.v1.features.face_profiles import schemas
from src.api.v1.features.face_profiles.service import FaceProfileService, get_face_profile_service
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import RoleName
from src.core.dependencies.auth import require_roles

router = APIRouter(prefix="/face-profiles", tags=["Face Profiles"])


@router.get("/employee/{employee_id}", response_model=schemas.FaceProfileRead)
async def get_face_profile_by_employee(
    employee_id: uuid.UUID,
    service: FaceProfileService = Depends(get_face_profile_service),
    current_user: User = Depends(
        require_roles(
            RoleName.admin,
            RoleName.hr,
            RoleName.manager,
            RoleName.employee,
        )
    ),
) -> schemas.FaceProfileRead:
    return await service.get_face_profile_by_employee(
        employee_id,
        current_user=current_user,
    )


@router.get("/{profile_id}", response_model=schemas.FaceProfileRead)
async def get_face_profile(
    profile_id: uuid.UUID,
    service: FaceProfileService = Depends(get_face_profile_service),
    current_user: User = Depends(
        require_roles(
            RoleName.admin,
            RoleName.hr,
            RoleName.manager,
            RoleName.employee,
        )
    ),
) -> schemas.FaceProfileRead:
    return await service.get_face_profile(profile_id, current_user=current_user)


@router.get("/", response_model=dict)
async def list_face_profiles(
    query: schemas.FaceProfileListQuery = Depends(),
    service: FaceProfileService = Depends(get_face_profile_service),
    current_user: User = Depends(
        require_roles(
            RoleName.admin,
            RoleName.hr,
            RoleName.manager,
            RoleName.employee,
        )
    ),
) -> dict:
    return await service.list_face_profiles(query, current_user=current_user)


@router.patch("/{profile_id}", response_model=schemas.FaceProfileRead)
async def update_face_profile(
    profile_id: uuid.UUID,
    payload: schemas.FaceProfileLifecycleUpdate,
    service: FaceProfileService = Depends(get_face_profile_service),
    current_user: User = Depends(require_roles(RoleName.admin, RoleName.hr)),
) -> schemas.FaceProfileRead:
    return await service.update_face_profile_for_actor(
        profile_id,
        schemas.FaceProfileUpdate(status=payload.status),
        current_user=current_user,
    )


@router.post("/{profile_id}/revoke", response_model=schemas.FaceProfileRead)
async def revoke_face_profile(
    profile_id: uuid.UUID,
    payload: schemas.RevokeFaceProfileRequest,
    service: FaceProfileService = Depends(get_face_profile_service),
    current_user: User = Depends(require_roles(RoleName.admin, RoleName.hr)),
) -> schemas.FaceProfileRead:
    return await service.revoke_face_profile(
        profile_id,
        payload,
        current_user=current_user,
    )
