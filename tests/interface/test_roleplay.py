"""Tests for interface/roleplay.py's Rolepost deletion listener."""

from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from beanie import PydanticObjectId

import interface.roleplay as roleplay_module
from bot import InconnuBot
from interface.roleplay import RoleplayCog
from models import VGuild

type MockBot = MagicMock
type MockChannel = AsyncMock

GUILD_ID = 1234
DELETION_CHANNEL_ID = 5678
MESSAGE_ID = 9012


@pytest.fixture
def deletion_channel() -> MockChannel:
    """The partial messageable that receives deletion notices."""
    return AsyncMock(spec=discord.PartialMessageable)


@pytest.fixture
def mock_bot(deletion_channel: MockChannel) -> MockBot:
    """A bot in the test guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = GUILD_ID
    guild.name = "Test Guild"

    bot = MagicMock(spec=InconnuBot)
    bot.get_or_fetch_guild = AsyncMock(return_value=guild)
    bot.get_partial_messageable.return_value = deletion_channel
    return bot


@pytest.fixture
def cog(mock_bot: MockBot) -> RoleplayCog:
    """The cog under test."""
    return RoleplayCog(mock_bot)


@pytest.fixture
def raw_message() -> discord.RawMessageDeleteEvent:
    """A deletion event for an uncached message."""
    event = MagicMock(spec=discord.RawMessageDeleteEvent)
    event.cached_message = None
    event.message_id = MESSAGE_ID
    return event


@pytest.fixture
def rp_post() -> dict[str, Any]:
    """A raw Rolepost document."""
    return {
        "_id": PydanticObjectId(),
        "guild": GUILD_ID,
        "user": 1,
        "channel": 2,
        "content": "The post content",
        "date": datetime(2026, 1, 1),
    }


@pytest.fixture
def mock_rp_posts(rp_post: dict[str, Any]) -> Generator[AsyncMock]:
    """The Rolepost collection, which finds the Rolepost."""
    collection = AsyncMock(spec=type(roleplay_module.db.rp_posts))
    collection.find_one_and_update.return_value = rp_post
    with patch.object(roleplay_module.db, "rp_posts", collection):
        yield collection


@pytest.fixture
async def vguild() -> AsyncGenerator[VGuild]:
    """The test guild's database document."""
    guild = VGuild(guild=GUILD_ID, name="Test Guild")
    await guild.save()
    yield guild
    await guild.delete()


async def test_deletion_notice_sent(
    cog: RoleplayCog,
    mock_bot: MockBot,
    deletion_channel: MockChannel,
    raw_message: discord.RawMessageDeleteEvent,
    mock_rp_posts: AsyncMock,
    vguild: VGuild,
):
    """A deleted Rolepost is reported in the guild's deletion channel."""
    vguild.settings.deletion_channel = DELETION_CHANNEL_ID
    await vguild.save()

    await cog.on_raw_message_delete(raw_message)

    mock_bot.get_partial_messageable.assert_called_once_with(DELETION_CHANNEL_ID)
    embed = deletion_channel.send.await_args.kwargs["embed"]
    assert "The post content" in embed.description


async def test_no_deletion_channel(
    cog: RoleplayCog,
    deletion_channel: MockChannel,
    raw_message: discord.RawMessageDeleteEvent,
    mock_rp_posts: AsyncMock,
    vguild: VGuild,
):
    """No notice is sent if the guild has no deletion channel."""
    await cog.on_raw_message_delete(raw_message)

    mock_rp_posts.find_one_and_update.assert_awaited_once()
    deletion_channel.send.assert_not_awaited()


async def test_guild_unavailable(
    cog: RoleplayCog,
    mock_bot: MockBot,
    deletion_channel: MockChannel,
    raw_message: discord.RawMessageDeleteEvent,
    mock_rp_posts: AsyncMock,
):
    """The post is still marked deleted if the guild can't be found."""
    mock_bot.get_or_fetch_guild.return_value = None

    await cog.on_raw_message_delete(raw_message)

    mock_rp_posts.find_one_and_update.assert_awaited_once()
    deletion_channel.send.assert_not_awaited()
