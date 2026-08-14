from __future__ import annotations

import asyncio
import json
import logging

import httpx
import pytest
from jose import jwt

from src.core.clients.chatbox.client import ChatboxClient
from src.core.clients.chatbox.schemas import ChatRequest
from src.core.configs.settings import settings
from src.core.security.authentication import (
    TokenError,
    create_access_token,
    decode_access_token,
)


def make_chat_request() -> ChatRequest:
    return ChatRequest(
        message="Tôi đi làm ca nào?",
        employee_id="00000000-0000-0000-0000-000000000001",
        user_role="employee",
        conversation_id="00000000-0000-0000-0000-000000000002",
    )


def test_chatbox_client_forwards_user_jwt_only_in_authorization_header(
    caplog: pytest.LogCaptureFixture,
) -> None:
    access_token = "request-scoped-secret-jwt"
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={"answer": "Ca hành chính"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://rag.test",
        ) as http_client:
            client = ChatboxClient(http_client)
            with caplog.at_level(logging.DEBUG):
                await client.chat(make_chat_request(), access_token=access_token)

    asyncio.run(run())

    assert captured_request is not None
    assert captured_request.headers["Authorization"] == f"Bearer {access_token}"
    request_body = json.loads(captured_request.content)
    assert "access_token" not in request_body
    assert access_token not in captured_request.content.decode()
    assert access_token not in caplog.text


def test_chatbox_client_rejects_empty_forwarded_token_without_request() -> None:
    request_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json={"answer": "unexpected"})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="http://rag.test",
        ) as http_client:
            client = ChatboxClient(http_client)
            try:
                await client.chat(make_chat_request(), access_token="   ")
            except ValueError as exc:
                assert str(exc) == "access_token must not be empty"
            else:
                raise AssertionError("empty token must be rejected")

    asyncio.run(run())
    assert request_count == 0


def test_access_token_has_expected_issuer_and_audience() -> None:
    token, _, _ = create_access_token(
        user_id="00000000-0000-0000-0000-000000000001",
        role="employee",
        token_version=0,
    )

    payload = decode_access_token(token)
    assert payload["iss"] == settings.jwt_issuer
    assert payload["aud"] == settings.jwt_audience


def test_access_token_with_wrong_audience_is_rejected() -> None:
    valid_token, _, _ = create_access_token(
        user_id="00000000-0000-0000-0000-000000000001",
        role="employee",
        token_version=0,
    )
    payload = jwt.get_unverified_claims(valid_token)
    payload["aud"] = "another-service"
    wrong_audience_token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(TokenError, match="Invalid access token"):
        decode_access_token(wrong_audience_token)


def test_expired_access_token_is_rejected() -> None:
    valid_token, _, _ = create_access_token(
        user_id="00000000-0000-0000-0000-000000000001",
        role="employee",
        token_version=0,
    )
    payload = jwt.get_unverified_claims(valid_token)
    payload["exp"] = 1
    expired_token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(TokenError, match="Invalid access token"):
        decode_access_token(expired_token)
