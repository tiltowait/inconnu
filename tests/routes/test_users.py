"""Tests for user routes."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from httpx import ASGITransport, AsyncClient

from config import settings
from routes.auth import DISCORD_HEADER
from server import app

TEST_API_KEY = "test-api-key-12345"
TEST_USER_ID = 987654321

type MockBot = MagicMock
type MockGuild = MagicMock


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


def make_guild(member: discord.Member | None) -> MockGuild:
    """A support server that finds the given member, or no one."""
    guild = MagicMock(spec=discord.Guild)
    guild.get_or_fetch = AsyncMock(return_value=member)
    return guild


def make_member(supporter: bool) -> discord.Member:
    """A support server member, with or without the supporter role."""
    member = MagicMock(spec=discord.Member)
    member.get_role.side_effect = lambda role_id: (
        MagicMock(spec=discord.Role) if supporter and role_id == settings.supporter_role else None
    )
    return member


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
async def test_check_premium_member(_app_bot: MockBot, client: AsyncClient, supporter: bool):
    """Support server members are supporters if they have the role."""
    guild = make_guild(make_member(supporter))
    _app_bot.get_or_fetch_guild = AsyncMock(return_value=guild)

    status, body = await check(client)
    assert status == 200
    assert body == {"is_supporter": supporter}
    _app_bot.get_or_fetch_guild.assert_awaited_once_with(settings.supporter_guild)
    guild.get_or_fetch.assert_awaited_once_with(discord.Member, TEST_USER_ID)


async def test_check_premium_not_on_support_server(_app_bot: MockBot, client: AsyncClient):
    """Users not on the support server aren't supporters."""
    _app_bot.get_or_fetch_guild = AsyncMock(return_value=make_guild(None))

    status, body = await check(client)
    assert status == 200
    assert body == {"is_supporter": False}


async def test_check_premium_no_support_server(_app_bot: MockBot, client: AsyncClient):
    """Without the support server, no one is a supporter."""
    _app_bot.get_or_fetch_guild = AsyncMock(return_value=None)

    status, body = await check(client)
    assert status == 200
    assert body == {"is_supporter": False}


async def test_check_premium_requires_api_key(client: AsyncClient):
    """The endpoint rejects requests without the API token."""
    status, _ = await check(client, auth=False)
    assert status == 401


async def test_check_premium_requires_user(client: AsyncClient):
    """The endpoint rejects requests without the user ID header."""
    status, _ = await check(client, user=False)
    assert status == 400
