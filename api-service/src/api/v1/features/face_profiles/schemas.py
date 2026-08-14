from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.api.v1.shared.datetime_utils import AppTimezoneModel
from src.api.v1.shared.enums import FaceProfileStatus


class FaceProfileBase(BaseModel):
    employee_id: uuid.UUID
    status: FaceProfileStatus = FaceProfileStatus.pending
    qdrant_collection: str = Field(..., min_length=1, max_length=120)
    embedding_model: str | None = Field(default=None, max_length=120)
    embedding_version: str | None = Field(default=None, max_length=120)
    registered_by: uuid.UUID | None = None
    revocation_reason: str | None = Field(default=None, max_length=1000)
    revoked_at: datetime | None = None

    @model_validator(mode="after")
    def validate_revocation_fields(self) -> "FaceProfileBase":
        if self.status == FaceProfileStatus.revoked:
            if not self.revoked_at:
                raise ValueError("revoked_at is required when status=revoked")
            if not self.revocation_reason:
                raise ValueError("revocation_reason is required when status=revoked")
        return self


class FaceProfileCreate(BaseModel):
    employee_id: uuid.UUID
    qdrant_collection: str = Field(..., min_length=1, max_length=120)
    registered_by: uuid.UUID | None = None


class FaceProfileUpdate(BaseModel):
    status: FaceProfileStatus | None = None
    qdrant_collection: str | None = Field(default=None, min_length=1, max_length=120)
    embedding_model: str | None = Field(default=None, max_length=120)
    embedding_version: str | None = Field(default=None, max_length=120)
    registered_by: uuid.UUID | None = None
    revocation_reason: str | None = Field(default=None, max_length=1000)
    revoked_at: datetime | None = None

    @model_validator(mode="after")
    def validate_revocation_fields(self) -> "FaceProfileUpdate":
        if self.status == FaceProfileStatus.revoked:
            if not self.revoked_at:
                raise ValueError("revoked_at is required when status=revoked")
            if not self.revocation_reason:
                raise ValueError("revocation_reason is required when status=revoked")
        return self


class FaceProfileLifecycleUpdate(BaseModel):
    """Public lifecycle mutation without vector-store implementation details."""

    status: FaceProfileStatus

    @model_validator(mode="after")
    def require_revoke_endpoint(self) -> "FaceProfileLifecycleUpdate":
        if self.status == FaceProfileStatus.revoked:
            raise ValueError("Use the dedicated revoke endpoint for revoked status")
        return self


class FaceProfileRead(AppTimezoneModel):
    """Client-safe projection of a face profile.

    Vector-store and embedding metadata deliberately stay internal to the face
    enrollment services. API consumers only need identity and lifecycle state.
    """

    model_config = ConfigDict(from_attributes=True)

    profile_id: uuid.UUID
    employee_id: uuid.UUID
    status: FaceProfileStatus
    created_at: datetime
    updated_at: datetime


class RevokeFaceProfileRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


class FaceProfileListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    employee_id: uuid.UUID | None = None
    status: FaceProfileStatus | None = None
