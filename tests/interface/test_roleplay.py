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
from services.webhooks import WebhookCache

type MockBot = MagicMock
type MockChannel = AsyncMock
type MockMessage = MagicMock

GUILD_ID = 1234
DELETION_CHANNEL_ID = 5678
MESSAGE_ID = 9012
WEBHOOK_ID = 3456


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
    bot.user = MagicMock(spec=discord.ClientUser)
    bot.webhook_cache = MagicMock(spec=WebhookCache)
    bot.webhook_cache.webhook_ids = {WEBHOOK_ID}
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


def cached_message(message_id: int, author_id: int, webhook_id: int | None) -> MockMessage:
    """A cached message."""
    message = MagicMock(spec=discord.Message, id=message_id, webhook_id=webhook_id)
    message.author = MagicMock(spec=discord.User, id=author_id, bot=webhook_id is not None)
    message.flags = MagicMock(spec=discord.MessageFlags, ephemeral=False)
    return message


def http_error[E: discord.HTTPException](cls: type[E]) -> E:
    """A Discord failure of the given type."""
    return cls(MagicMock(status=500, reason="Error"), "Failed")


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


@pytest.mark.parametrize("error", [discord.Forbidden, discord.HTTPException])
async def test_deletion_notice_failure_is_ignored(
    cog: RoleplayCog,
    deletion_channel: MockChannel,
    raw_message: discord.RawMessageDeleteEvent,
    mock_rp_posts: AsyncMock,
    vguild: VGuild,
    error: type[discord.HTTPException],
):
    """A broken deletion channel doesn't raise an error."""
    vguild.settings.deletion_channel = DELETION_CHANNEL_ID
    await vguild.save()
    deletion_channel.send.side_effect = http_error(error)

    await cog.on_raw_message_delete(raw_message)

    deletion_channel.send.assert_awaited_once()


async def test_deleted_post_is_marked(
    cog: RoleplayCog,
    raw_message: discord.RawMessageDeleteEvent,
    mock_rp_posts: AsyncMock,
    vguild: VGuild,
):
    """The Rolepost with the deleted message's ID is marked deleted."""
    await cog.on_raw_message_delete(raw_message)

    query, update = mock_rp_posts.find_one_and_update.await_args.args
    assert query == {"message_id": MESSAGE_ID}
    assert update["$set"]["deleted"] is True
    assert update["$set"]["deletion_date"] is not None


async def test_deleted_message_is_not_a_rolepost(
    cog: RoleplayCog,
    mock_bot: MockBot,
    raw_message: discord.RawMessageDeleteEvent,
    mock_rp_posts: AsyncMock,
):
    """A deleted message with no Rolepost is ignored."""
    mock_rp_posts.find_one_and_update.return_value = None

    await cog.on_raw_message_delete(raw_message)

    mock_bot.get_or_fetch_guild.assert_not_awaited()


@pytest.mark.parametrize("from_bot", [False, True])
async def test_cached_non_webhook_message_skips_database(
    cog: RoleplayCog,
    raw_message: discord.RawMessageDeleteEvent,
    mock_rp_posts: AsyncMock,
    from_bot: bool,
):
    """A cached message without a webhook can't be a Rolepost, even from a bot."""
    message = cached_message(MESSAGE_ID, 1, webhook_id=None)
    message.author.bot = from_bot
    raw_message.cached_message = message

    await cog.on_raw_message_delete(raw_message)

    mock_rp_posts.find_one_and_update.assert_not_awaited()


async def test_cached_webhook_message_is_marked(
    cog: RoleplayCog,
    raw_message: discord.RawMessageDeleteEvent,
    mock_rp_posts: AsyncMock,
    vguild: VGuild,
):
    """A cached webhook message may be a Rolepost."""
    raw_message.cached_message = cached_message(MESSAGE_ID, WEBHOOK_ID, webhook_id=WEBHOOK_ID)

    await cog.on_raw_message_delete(raw_message)

    mock_rp_posts.find_one_and_update.assert_awaited_once()


async def test_bulk_delete_marks_possible_roleposts(cog: RoleplayCog, mock_rp_posts: AsyncMock):
    """Bulk deletions mark cached webhook messages and uncached messages, but not
    cached messages from users."""
    webhook_message = cached_message(1, WEBHOOK_ID, webhook_id=WEBHOOK_ID)
    user_message = cached_message(2, 100, webhook_id=None)
    payload = MagicMock(spec=discord.RawBulkMessageDeleteEvent)
    payload.message_ids = {1, 2, 3}
    payload.cached_messages = [webhook_message, user_message]

    await cog.on_raw_bulk_message_delete(payload)

    updates = mock_rp_posts.bulk_write.await_args.args[0]
    assert sorted(update._filter["message_id"] for update in updates) == [1, 3]
    for update in updates:
        assert update._doc["$set"]["deleted"] is True


async def test_bulk_delete_of_only_user_messages(cog: RoleplayCog, mock_rp_posts: AsyncMock):
    """With nothing that could be a Rolepost, the database isn't touched."""
    payload = MagicMock(spec=discord.RawBulkMessageDeleteEvent)
    payload.message_ids = {1}
    payload.cached_messages = [cached_message(1, 100, webhook_id=None)]

    await cog.on_raw_bulk_message_delete(payload)

    mock_rp_posts.bulk_write.assert_not_awaited()


async def test_channel_delete_marks_its_roleposts(cog: RoleplayCog, mock_rp_posts: AsyncMock):
    """Deleting a channel marks every Rolepost in it as deleted."""
    channel = MagicMock(spec=discord.TextChannel, id=4321)
    channel.name = "scene"

    await cog.on_guild_channel_delete(channel)

    query, update = mock_rp_posts.update_many.await_args.args
    assert query == {"channel": 4321}
    assert update["$set"]["deleted"] is True
