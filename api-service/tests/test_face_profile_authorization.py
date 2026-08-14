from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.features.face_profiles import schemas
from src.api.v1.features.face_profiles.controller import router
from src.api.v1.features.face_profiles.face_profile_repo import FaceProfileRepo
from src.api.v1.features.face_profiles.service import (
    FaceProfileService,
    get_face_profile_service,
)
from src.api.v1.features.users.models import User
from src.api.v1.shared.enums import FaceProfileStatus, RoleName
from src.core.clients.face_server.clients import FaceServerClient
from src.core.security.authorization import AuthorizationPolicy
from src.utils.exeptions import ForbiddenException


class FakeScalarResult:
    def __init__(self, values: set[uuid.UUID]) -> None:
        self.values = values

    def scalars(self) -> FakeScalarResult:
        return self

    def all(self) -> list[uuid.UUID]:
        return list(self.values)


class FakePolicyDB:
    def __init__(
        self,
        current_employee_id: uuid.UUID,
        *,
        manager_scope: set[uuid.UUID] | None = None,
    ) -> None:
        self.current_employee_id = current_employee_id
        self.manager_scope = manager_scope or set()

    async def scalar(self, _statement):
        return self.current_employee_id

    async def execute(self, _statement):
        return FakeScalarResult(self.manager_scope)


class FakeFaceProfileRepo:
    def __init__(self, profiles: list[SimpleNamespace]) -> None:
        self.profiles = profiles
        self.last_visible_employee_ids: set[uuid.UUID] | None = None

    async def get_profile_by_id(self, profile_id: uuid.UUID):
        return next(
            (profile for profile in self.profiles if profile.profile_id == profile_id),
            None,
        )

    async def get_profile_by_employee_id(self, employee_id: uuid.UUID):
        return next(
            (profile for profile in self.profiles if profile.employee_id == employee_id),
            None,
        )

    async def list_face_profiles(
        self,
        *,
        page: int,
        page_size: int,
        employee_id: uuid.UUID | None,
        status: FaceProfileStatus | None,
        visible_employee_ids: set[uuid.UUID] | None,
    ):
        self.last_visible_employee_ids = visible_employee_ids
        items = self.profiles
        if visible_employee_ids is not None:
            items = [
                profile
                for profile in items
                if profile.employee_id in visible_employee_ids
            ]
        if employee_id is not None:
            items = [
                profile for profile in items if profile.employee_id == employee_id
            ]
        if status is not None:
            items = [profile for profile in items if profile.status == status]
        offset = (page - 1) * page_size
        return items[offset : offset + page_size], len(items)


class RecordingDB:
    def __init__(self) -> None:
        self.list_statement = None

    async def scalar(self, _statement):
        return 0

    async def execute(self, statement):
        self.list_statement = statement
        return FakeScalarResult(set())


def make_user(role_name: RoleName) -> User:
    return cast(
        User,
        SimpleNamespace(user_id=uuid.uuid4(), role_name=role_name),
    )


def make_profile(employee_id: uuid.UUID) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        profile_id=uuid.uuid4(),
        employee_id=employee_id,
        status=FaceProfileStatus.active,
        qdrant_collection="internal-face-vectors",
        embedding_model="internal-model",
        embedding_version="internal-version",
        registered_by=uuid.uuid4(),
        revocation_reason="internal-reason",
        revoked_at=now,
        created_at=now,
        updated_at=now,
    )


def make_service(
    *,
    current_employee_id: uuid.UUID,
    profiles: list[SimpleNamespace],
    manager_scope: set[uuid.UUID] | None = None,
) -> tuple[FaceProfileService, FakeFaceProfileRepo]:
    repo = FakeFaceProfileRepo(profiles)
    policy = AuthorizationPolicy(
        cast(
            AsyncSession,
            FakePolicyDB(
                current_employee_id,
                manager_scope=manager_scope,
            ),
        )
    )
    service = FaceProfileService(
        face_profile_repo=cast(FaceProfileRepo, repo),
        face_server_client=cast(FaceServerClient, None),
        authorization_policy=policy,
    )
    return service, repo


def test_employee_can_read_only_own_face_profile() -> None:
    own_employee_id = uuid.uuid4()
    other_employee_id = uuid.uuid4()
    own_profile = make_profile(own_employee_id)
    other_profile = make_profile(other_employee_id)
    service, _ = make_service(
        current_employee_id=own_employee_id,
        profiles=[own_profile, other_profile],
    )
    actor = make_user(RoleName.employee)

    own = asyncio.run(
        service.get_face_profile_by_employee(
            own_employee_id,
            current_user=actor,
        )
    )
    assert own.employee_id == own_employee_id
    assert "qdrant_collection" not in own.model_dump()
    assert "embedding_model" not in own.model_dump()
    assert "revocation_reason" not in own.model_dump()

    with pytest.raises(ForbiddenException):
        asyncio.run(
            service.get_face_profile_by_employee(
                other_employee_id,
                current_user=actor,
            )
        )


def test_manager_can_read_subordinate_but_not_employee_outside_scope() -> None:
    manager_id = uuid.uuid4()
    subordinate_id = uuid.uuid4()
    outside_id = uuid.uuid4()
    subordinate = make_profile(subordinate_id)
    outside = make_profile(outside_id)
    service, _ = make_service(
        current_employee_id=manager_id,
        profiles=[subordinate, outside],
        manager_scope={manager_id, subordinate_id},
    )
    actor = make_user(RoleName.manager)

    result = asyncio.run(
        service.get_face_profile(
            subordinate.profile_id,
            current_user=actor,
        )
    )
    assert result.employee_id == subordinate_id

    with pytest.raises(ForbiddenException):
        asyncio.run(
            service.get_face_profile(
                outside.profile_id,
                current_user=actor,
            )
        )


def test_manager_list_is_scoped_before_repository_query() -> None:
    manager_id = uuid.uuid4()
    subordinate_id = uuid.uuid4()
    outside_id = uuid.uuid4()
    service, repo = make_service(
        current_employee_id=manager_id,
        profiles=[make_profile(subordinate_id), make_profile(outside_id)],
        manager_scope={manager_id, subordinate_id},
    )

    result = asyncio.run(
        service.list_face_profiles(
            schemas.FaceProfileListQuery(),
            current_user=make_user(RoleName.manager),
        )
    )

    assert {item.employee_id for item in result["items"]} == {subordinate_id}
    assert repo.last_visible_employee_ids == {manager_id, subordinate_id}


@pytest.mark.parametrize("role_name", [RoleName.hr, RoleName.admin])
def test_hr_and_admin_follow_global_face_profile_policy(role_name: RoleName) -> None:
    employee_ids = {uuid.uuid4(), uuid.uuid4()}
    service, repo = make_service(
        current_employee_id=uuid.uuid4(),
        profiles=[make_profile(employee_id) for employee_id in employee_ids],
    )

    result = asyncio.run(
        service.list_face_profiles(
            schemas.FaceProfileListQuery(),
            current_user=make_user(role_name),
        )
    )

    assert {item.employee_id for item in result["items"]} == employee_ids
    assert repo.last_visible_employee_ids is None


def test_repository_applies_visible_employee_filter_in_sql() -> None:
    db = RecordingDB()
    repo = FaceProfileRepo(cast(AsyncSession, db))
    visible_ids = {uuid.uuid4(), uuid.uuid4()}

    asyncio.run(repo.list_face_profiles(visible_employee_ids=visible_ids))

    assert db.list_statement is not None
    compiled = str(
        db.list_statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "face_profiles.employee_id IN" in compiled
    for employee_id in visible_ids:
        assert str(employee_id) in compiled


def test_rag_api_key_alone_cannot_read_face_profile_metadata() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_face_profile_service] = lambda: object()

    response = TestClient(app).get(
        f"/api/v1/face-profiles/{uuid.uuid4()}",
        headers={"Rag-API-Key": "not-a-user-token"},
    )

    assert response.status_code in {401, 403}


def test_public_face_profile_update_schema_exposes_only_lifecycle_status() -> None:
    schema = schemas.FaceProfileLifecycleUpdate.model_json_schema()
    assert set(schema["properties"]) == {"status"}
