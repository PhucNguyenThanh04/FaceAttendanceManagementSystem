from __future__ import annotations

import uuid

import httpx
from fastapi import Depends

from src.api.v1.features.face_profiles import schemas
from src.api.v1.features.face_profiles.face_profile_repo import (
    FaceProfileRepo,
    get_face_profile_repo,
)
from src.api.v1.shared.enums import FaceProfileStatus
from src.core.clients.face_server.clients import FaceServerClient
from src.core.clients.face_server.schemas import (
    AIAddPhotoResponse,
    AICancelEnrollmentResponse,
    AICommitRequest,
    AICommitResponse,
)
from src.core.dependencies.dep import get_ai_http_client
from src.utils.exeptions import BadRequestException, MLProcessingException, NotFoundException
from src.utils.setup_logger import setup_logger

logger = setup_logger(__name__)


class FaceProfileService:
    def __init__(self, face_profile_repo: FaceProfileRepo, face_server_client: FaceServerClient):
        self.face_profile_repo = face_profile_repo
        self.face_server_client = face_server_client

    @staticmethod
    def _to_read(profile) -> schemas.FaceProfileRead:
        return schemas.FaceProfileRead.model_validate(profile)

    async def create_face_profile(self, payload: schemas.FaceProfileCreate) -> schemas.FaceProfileRead:
        if not await self.face_profile_repo.employee_exists(payload.employee_id):
            raise BadRequestException("Employee not found")
        if payload.registered_by is not None and not await self.face_profile_repo.user_exists(
            payload.registered_by
        ):
            raise BadRequestException("Registrar user not found")

        profile = await self.face_profile_repo.create_face_profile(payload)
        logger.info("Face profile created: profile_id=%s", profile.profile_id)
        return self._to_read(profile)

    async def get_face_profile(self, profile_id: uuid.UUID) -> schemas.FaceProfileRead:
        profile = await self.face_profile_repo.get_profile_by_id(profile_id)
        if profile is None:
            logger.warning("Face profile not found: profile_id=%s", profile_id)
            raise NotFoundException("Face profile")
        return self._to_read(profile)

    async def get_face_profile_by_employee(self, employee_id: uuid.UUID) -> schemas.FaceProfileRead:
        profile = await self.face_profile_repo.get_profile_by_employee_id(employee_id)
        if profile is None:
            logger.warning("Face profile not found by employee: employee_id=%s", employee_id)
            raise NotFoundException("Face profile")
        return self._to_read(profile)

    async def list_face_profiles(self, query: schemas.FaceProfileListQuery) -> dict:
        profiles, total = await self.face_profile_repo.list_face_profiles(
            page=query.page,
            page_size=query.page_size,
            employee_id=query.employee_id,
            status=query.status,
        )
        return {
            "items": [self._to_read(profile) for profile in profiles],
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
        }

    async def update_face_profile(
        self,
        profile_id: uuid.UUID,
        payload: schemas.FaceProfileUpdate,
    ) -> schemas.FaceProfileRead:
        existing = await self.face_profile_repo.get_profile_by_id(profile_id)
        if existing is None:
            raise NotFoundException("Face profile")

        if payload.registered_by is not None and not await self.face_profile_repo.user_exists(
            payload.registered_by
        ):
            raise BadRequestException("Registrar user not found")

        updated = await self.face_profile_repo.update_face_profile(profile_id, payload)
        logger.info("Face profile updated: profile_id=%s", profile_id)
        return self._to_read(updated)

    async def revoke_face_profile(
        self,
        profile_id: uuid.UUID,
        payload: schemas.RevokeFaceProfileRequest,
    ) -> schemas.FaceProfileRead:
        revoked = await self.face_profile_repo.revoke_face_profile(profile_id, payload.reason)
        logger.info("Face profile revoked: profile_id=%s", profile_id)
        return self._to_read(revoked)

    async def delete_face_profile(self, profile_id: uuid.UUID) -> None:
        existing = await self.face_profile_repo.get_profile_by_id(profile_id)
        if existing is None:
            raise NotFoundException("Face profile")
        await self.face_profile_repo.delete_face_profile(profile_id)
        logger.info("Face profile deleted: profile_id=%s", profile_id)

    # ---- Methods for employee_onboarding orchestration ----
    async def ensure_pending_profile_for_onboarding(
        self,
        *,
        employee_id: uuid.UUID,
        qdrant_collection: str,
        registered_by: uuid.UUID | None = None,
    ) -> schemas.FaceProfileRead:
        if not await self.face_profile_repo.employee_exists(employee_id):
            raise BadRequestException("Employee not found")
        if registered_by is not None and not await self.face_profile_repo.user_exists(registered_by):
            raise BadRequestException("Registrar user not found")
        profile = await self.face_profile_repo.ensure_pending_profile(
            employee_id=employee_id,
            qdrant_collection=qdrant_collection,
            registered_by=registered_by,
        )
        return self._to_read(profile)

    async def mark_profile_active_for_onboarding(
        self,
        *,
        profile_id: uuid.UUID,
        embedding_model: str | None = None,
        embedding_version: str | None = None,
    ) -> schemas.FaceProfileRead:
        profile = await self.face_profile_repo.mark_profile_active(
            profile_id=profile_id,
            embedding_model=embedding_model,
            embedding_version=embedding_version,
        )
        return self._to_read(profile)

    async def add_enrollment_photo(
        self,
        *,
        session_id: str,
        image_bytes: bytes,
        filename: str = "face.jpg",
        content_type: str = "image/jpeg",
    ) -> AIAddPhotoResponse:
        try:
            return await self.face_server_client.add_photo(
                session_id=session_id,
                image_bytes=image_bytes,
                filename=filename,
                content_type=content_type,
            )
        except httpx.HTTPError as exc:
            logger.exception("AI add_photo failed: session_id=%s", session_id)
            raise MLProcessingException(step="add_photo", reason=str(exc)) from exc

    async def commit_enrollment(self, body: AICommitRequest) -> AICommitResponse:
        try:
            return await self.face_server_client.commit(body)
        except httpx.HTTPError as exc:
            logger.exception("AI commit failed: session_id=%s", body.session_id)
            raise MLProcessingException(step="commit", reason=str(exc)) from exc

    async def re_enroll(self, body: AICommitRequest) -> AICommitResponse:
        try:
            return await self.face_server_client.re_enroll(body)
        except httpx.HTTPError as exc:
            logger.exception("AI re_enroll failed: session_id=%s", body.session_id)
            raise MLProcessingException(step="re_enroll", reason=str(exc)) from exc

    async def cancel_enrollment(self, session_id: str) -> AICancelEnrollmentResponse:
        try:
            return await self.face_server_client.cancel_enrollment(session_id)
        except httpx.HTTPError as exc:
            logger.exception("AI cancel enrollment failed: session_id=%s", session_id)
            raise MLProcessingException(step="cancel_enrollment", reason=str(exc)) from exc

    async def mark_profile_failed(self, profile_id: uuid.UUID, reason: str | None = None) -> schemas.FaceProfileRead:
        update = schemas.FaceProfileUpdate(
            status=FaceProfileStatus.failed,
            revocation_reason=reason,
        )
        profile = await self.face_profile_repo.update_face_profile(profile_id, update)
        return self._to_read(profile)


def get_face_profile_service(
    face_profile_repo: FaceProfileRepo = Depends(get_face_profile_repo),
    ai_http_client: httpx.AsyncClient = Depends(get_ai_http_client),
) -> FaceProfileService:
    return FaceProfileService(
        face_profile_repo=face_profile_repo,
        face_server_client=FaceServerClient(ai_http_client),
    )
