from __future__ import annotations

from typing import Any, cast

import pytest

from src.api.v1.features.employee_onboarding.service import EmployeeOnboardingService
from src.core.exceptions import UploadQuotaExceededException


class FakeRedis:
    def __init__(self, attempt_count: int) -> None:
        self.attempt_count = attempt_count
        self.calls: list[tuple[Any, ...]] = []

    async def eval(self, *args: Any) -> int:
        self.calls.append(args)
        return self.attempt_count


def make_service(redis_client: FakeRedis) -> EmployeeOnboardingService:
    return EmployeeOnboardingService(
        employee_service=cast(Any, object()),
        face_profile_service=cast(Any, object()),
        user_service=cast(Any, object()),
        face_server_client=cast(Any, object()),
        redis_client=cast(Any, redis_client),
    )


@pytest.mark.asyncio
async def test_onboarding_upload_attempt_within_quota_is_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = FakeRedis(attempt_count=20)
    service = make_service(redis_client)
    monkeypatch.setattr(
        "src.api.v1.features.employee_onboarding.service."
        "settings.onboarding_max_upload_attempts_per_session",
        20,
    )

    await service._consume_upload_attempt("session-id", 60)

    assert len(redis_client.calls) == 1
    assert redis_client.calls[0][2] == "onboarding:upload-attempts:session-id"


@pytest.mark.asyncio
async def test_onboarding_upload_attempt_over_quota_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = FakeRedis(attempt_count=21)
    service = make_service(redis_client)
    monkeypatch.setattr(
        "src.api.v1.features.employee_onboarding.service."
        "settings.onboarding_max_upload_attempts_per_session",
        20,
    )

    with pytest.raises(UploadQuotaExceededException) as exc_info:
        await service._consume_upload_attempt("session-id", 60)

    assert exc_info.value.status_code == 429
