"""Tests for user routes."""

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from config import settings
from routes.auth import DISCORD_HEADER
from server import app
from services import premium

TEST_API_KEY = "test-api-key-12345"
TEST_USER_ID = 987654321


@pytest.fixture(autouse=True)
def mock_api_key():
    """Pin the configured API token for each test."""
    with patch.object(settings, "inconnu_api_token", TEST_API_KEY):
        yield


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    """An HTTP client for the app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def check(client: AsyncClient, *, auth=True, user=True) -> tuple[int, dict]:
    """Request the test user's premium status."""
    headers = {}
    if auth:
        headers["Authorization"] = f"Bearer {TEST_API_KEY}"
    if user:
        headers[DISCORD_HEADER] = str(TEST_USER_ID)
    response = await client.get("/users/check-premium", headers=headers)
    return response.status_code, response.json()


@pytest.mark.parametrize("supporter", [True, False])
async def test_check_premium(client: AsyncClient, supporter: bool):
    """The endpoint reports whether the requester is a supporter."""
    with patch.object(premium, "_supporters", {TEST_USER_ID} if supporter else set()):
        status, body = await check(client)

    assert status == 200
    assert body == {"is_supporter": supporter}


async def test_check_premium_requires_api_key(client: AsyncClient):
    """The endpoint rejects requests without the API token."""
    status, _ = await check(client, auth=False)
    assert status == 401


async def test_check_premium_requires_user(client: AsyncClient):
    """The endpoint rejects requests without the user ID header."""
    status, _ = await check(client, user=False)
    assert status == 400
