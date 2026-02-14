"""Tests for rolepost changelog routes."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from beanie import PydanticObjectId, init_beanie
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from pymongo import AsyncMongoClient

import db as database
from models import RPPost
from models.rpheader import DamageSubdoc, HeaderSubdoc
from server import app

# Test constants
TEST_API_KEY = "test-api-key-12345"
TEST_GUILD_ID = 123456789
TEST_CHANNEL_ID = 111111111
TEST_USER_ID = 987654321
TEST_CHAR_ID = PydanticObjectId()


@pytest.fixture(autouse=True, scope="function")
async def mock_beanie():
    """Initialize mock database for each test."""
    client = cast(AsyncMongoClient, AsyncMongoMockClient())
    mock_db = client.get_database("test")
    await init_beanie(mock_db, document_models=database.models())

    with patch.object(database, "characters", mock_db.characters):
        yield


@pytest.fixture(autouse=True)
def mock_api_key():
    """Mock API_KEY for all tests."""
    with patch("routes.auth.API_KEY", TEST_API_KEY):
        yield


def auth_headers() -> dict[str, str]:
    """Standard auth headers."""
    return {"Authorization": f"Bearer {TEST_API_KEY}"}


def make_header_subdoc() -> HeaderSubdoc:
    """Create a minimal HeaderSubdoc."""
    return HeaderSubdoc(
        charid=TEST_CHAR_ID,
        char_name="Nadea",
        blush=0,
        hunger=2,
        location="Elysium",
        merits="",
        flaws="",
        temp="",
        health=DamageSubdoc(superficial=0, aggravated=0),
        willpower=DamageSubdoc(superficial=0, aggravated=0),
    )


async def insert_rolepost(**overrides) -> RPPost:
    """Insert an RPPost into the mock database."""
    defaults = dict(
        guild=TEST_GUILD_ID,
        channel=TEST_CHANNEL_ID,
        user=TEST_USER_ID,
        message_id=555555555,
        header=make_header_subdoc(),
        content="Test rolepost content",
        url="https://discord.com/channels/1/2/3",
    )
    defaults.update(overrides)
    post = RPPost(**defaults)
    await post.insert()
    return post


def make_mock_guild() -> MagicMock:
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = TEST_GUILD_ID
    guild.name = "Test Guild"
    guild.icon = None
    return guild


def make_mock_member() -> MagicMock:
    """Create a mock Discord member."""
    member = MagicMock(spec=discord.Member)
    member.id = TEST_USER_ID
    member.display_name = "TestUser"

    avatar = MagicMock(spec=discord.Asset)
    avatar.url = "https://cdn.discordapp.com/avatars/test.png"
    member.display_avatar = avatar
    member.guild_avatar = None
    return member


def make_mock_channel() -> MagicMock:
    """Create a mock Discord channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = "rp-channel"
    return channel


async def test_rolepost_not_found():
    """Returns 404 when the rolepost doesn't exist."""
    fake_id = PydanticObjectId()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/changelog/{fake_id}", headers=auth_headers())
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Rolepost not found"


async def test_guild_gone():
    """Returns 410 when the bot is no longer in the guild."""
    post = await insert_rolepost()
    bot = MagicMock()
    bot.get_or_fetch_guild = AsyncMock(return_value=None)
    with patch("routes.roleposts.inconnu.bot", bot):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/changelog/{post.id}", headers=auth_headers())
    assert resp.status_code == 410
    assert resp.json()["detail"] == "Inconnu is not in this guild."


async def test_channel_gone():
    """Returns 410 when the post's channel has been deleted."""
    post = await insert_rolepost()
    guild = make_mock_guild()
    guild.get_or_fetch = AsyncMock(return_value=None)

    bot = MagicMock()
    bot.get_or_fetch_guild = AsyncMock(return_value=guild)
    with patch("routes.roleposts.inconnu.bot", bot):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/changelog/{post.id}", headers=auth_headers())
    assert resp.status_code == 410
    assert resp.json()["detail"] == "This post's channel was deleted."


async def test_success_with_poster():
    """Returns full changelog when member is in the guild."""
    post = await insert_rolepost()
    guild = make_mock_guild()
    channel = make_mock_channel()
    member = make_mock_member()

    guild.get_or_fetch = AsyncMock(return_value=channel)
    guild.get_member.return_value = member

    bot = MagicMock()
    bot.get_or_fetch_guild = AsyncMock(return_value=guild)
    with patch("routes.roleposts.inconnu.bot", bot):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/changelog/{post.id}", headers=auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["guild"]["name"] == "Test Guild"
    assert data["poster"]["name"] == "TestUser"
    assert data["channel"] == "rp-channel"
    assert data["character"]["name"] == "Nadea"
    assert data["history"][0]["content"] == "Test rolepost content"
    assert data["deletion_date"] is None


async def test_success_without_poster():
    """Returns changelog with null poster when member left the guild."""
    post = await insert_rolepost()
    guild = make_mock_guild()
    channel = make_mock_channel()

    guild.get_or_fetch = AsyncMock(return_value=channel)
    guild.get_member.return_value = None

    bot = MagicMock()
    bot.get_or_fetch_guild = AsyncMock(return_value=guild)
    with patch("routes.roleposts.inconnu.bot", bot):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/changelog/{post.id}", headers=auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["poster"] is None
    assert data["character"]["name"] == "Nadea"


async def test_auth_required():
    """Returns 401 when no auth header is provided."""
    fake_id = PydanticObjectId()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/changelog/{fake_id}")
    assert resp.status_code == 401
