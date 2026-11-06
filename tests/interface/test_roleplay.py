"""Tests for interface/roleplay.py's Rolepost deletion listener."""

from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import discord
import pytest
from beanie import PydanticObjectId
from pydantic import AnyUrl

import interface.roleplay as roleplay_module
from bot import InconnuBot
from interface.roleplay import RoleplayCog
from models import RPPost, VGuild
from models.rpheader import DamageSubdoc, HeaderSubdoc
from services.webhooks import WebhookCache

type MockBot = MagicMock
type MockChannel = AsyncMock
type MockMessage = MagicMock
type PostSaver = Callable[..., Awaitable[RPPost]]

GUILD_ID = 1234
DELETION_CHANNEL_ID = 5678
MESSAGE_ID = 9012
WEBHOOK_ID = 3456
BULK_CHANNEL_ID = 7890


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
async def save_post() -> AsyncGenerator[PostSaver]:
    """Saves Roleposts to the database, removing them after the test."""

    async def saver(message_id=MESSAGE_ID, content="The post content", **kwargs: Any) -> RPPost:
        """Save a Rolepost."""
        damage = DamageSubdoc(superficial=0, aggravated=0)
        post = RPPost(
            guild=GUILD_ID,
            channel=2,
            user=1,
            message_id=message_id,
            url=AnyUrl(f"https://discord.com/channels/{GUILD_ID}/2/{message_id}"),
            content=content,
            header=HeaderSubdoc(
                charid=PydanticObjectId(),
                char_name="Nadea",
                blush=-1,
                hunger=1,
                location="",
                merits="",
                flaws="",
                temp="",
                health=damage,
                willpower=damage,
            ),
            **kwargs,
        )
        await post.save()
        return post

    yield saver
    await RPPost.delete_all()


@pytest.fixture
def mock_rp_posts() -> Generator[AsyncMock]:
    """The raw Rolepost collection, for the writes mongomock's client can't reach."""
    collection = AsyncMock(spec=type(roleplay_module.db.rp_posts))
    with patch.object(roleplay_module.db, "rp_posts", collection):
        yield collection


async def is_deleted(post: RPPost) -> bool:
    """Whether the database has the post marked as deleted."""
    saved = await RPPost.get(post.id)  # pyright: ignore[reportArgumentType]
    assert saved is not None
    return saved.deleted


def cached_message(message_id: int, author_id: int, webhook_id: int | None) -> MockMessage:
    """A cached message."""
    message = MagicMock(spec=discord.Message, id=message_id, webhook_id=webhook_id)
    message.author = MagicMock(spec=discord.User, id=author_id, bot=webhook_id is not None)
    message.flags = MagicMock(spec=discord.MessageFlags, ephemeral=False)
    return message


def http_error[E: discord.HTTPException](cls: type[E]) -> E:
    """A Discord failure of the given type."""
    return cls(MagicMock(status=500, reason="Error"), "Failed")


def bulk_event(*cached: MockMessage, ids: set[int]) -> discord.RawBulkMessageDeleteEvent:
    """A bulk deletion event in the test guild."""
    payload = MagicMock(spec=discord.RawBulkMessageDeleteEvent)
    payload.guild_id = GUILD_ID
    payload.channel_id = BULK_CHANNEL_ID
    payload.message_ids = ids
    payload.cached_messages = list(cached)
    return payload


@pytest.fixture
async def vguild() -> AsyncGenerator[VGuild]:
    """The test guild's database document."""
    guild = VGuild(guild=GUILD_ID, name="Test Guild")
    await guild.save()
    yield guild
    await guild.delete()


@pytest.fixture
async def deletion_guild(vguild: VGuild) -> VGuild:
    """The test guild, with a deletion channel."""
    vguild.settings.deletion_channel = DELETION_CHANNEL_ID
    await vguild.save()
    return vguild


# Test on_raw_message_delete


async def test_deletion_notice_sent(
    cog: RoleplayCog,
    mock_bot: MockBot,
    deletion_channel: MockChannel,
    raw_message: discord.RawMessageDeleteEvent,
    save_post: PostSaver,
    deletion_guild: VGuild,
):
    """A deleted Rolepost is reported in the guild's deletion channel."""
    await save_post()

    await cog.on_raw_message_delete(raw_message)

    mock_bot.get_partial_messageable.assert_called_once_with(DELETION_CHANNEL_ID)
    embed = deletion_channel.send.await_args.kwargs["embed"]
    assert "The post content" in embed.description


async def test_no_deletion_channel(
    cog: RoleplayCog,
    deletion_channel: MockChannel,
    raw_message: discord.RawMessageDeleteEvent,
    save_post: PostSaver,
    vguild: VGuild,
):
    """No notice is sent if the guild has no deletion channel."""
    post = await save_post()

    await cog.on_raw_message_delete(raw_message)

    assert await is_deleted(post)
    deletion_channel.send.assert_not_awaited()


async def test_guild_unavailable(
    cog: RoleplayCog,
    mock_bot: MockBot,
    deletion_channel: MockChannel,
    raw_message: discord.RawMessageDeleteEvent,
    save_post: PostSaver,
):
    """The post is still marked deleted if the guild can't be found."""
    post = await save_post()
    mock_bot.get_or_fetch_guild.return_value = None

    await cog.on_raw_message_delete(raw_message)

    assert await is_deleted(post)
    deletion_channel.send.assert_not_awaited()


@pytest.mark.parametrize("error", [discord.Forbidden, discord.HTTPException])
async def test_deletion_notice_failure_is_ignored(
    cog: RoleplayCog,
    deletion_channel: MockChannel,
    raw_message: discord.RawMessageDeleteEvent,
    save_post: PostSaver,
    deletion_guild: VGuild,
    error: type[discord.HTTPException],
):
    """A broken deletion channel doesn't raise an error."""
    await save_post()
    deletion_channel.send.side_effect = http_error(error)

    await cog.on_raw_message_delete(raw_message)

    deletion_channel.send.assert_awaited_once()


async def test_deleted_post_is_marked(
    cog: RoleplayCog,
    raw_message: discord.RawMessageDeleteEvent,
    save_post: PostSaver,
    vguild: VGuild,
):
    """Only the Rolepost with the deleted message's ID is marked, with the date."""
    post = await save_post()
    other_post = await save_post(MESSAGE_ID + 1)

    await cog.on_raw_message_delete(raw_message)

    saved = await RPPost.get(post.id)  # pyright: ignore[reportArgumentType]
    assert saved is not None
    assert saved.deleted is True
    assert saved.deletion_date is not None
    assert not await is_deleted(other_post)


async def test_deleted_message_is_not_a_rolepost(
    cog: RoleplayCog,
    mock_bot: MockBot,
    raw_message: discord.RawMessageDeleteEvent,
    save_post: PostSaver,
):
    """A deleted message with no Rolepost is ignored."""
    await cog.on_raw_message_delete(raw_message)

    mock_bot.get_or_fetch_guild.assert_not_awaited()


@pytest.mark.parametrize("from_bot", [False, True])
async def test_cached_non_webhook_message_is_ignored(
    cog: RoleplayCog,
    raw_message: discord.RawMessageDeleteEvent,
    save_post: PostSaver,
    from_bot: bool,
):
    """A cached message without a webhook can't be a Rolepost, even from a bot."""
    post = await save_post()
    message = cached_message(MESSAGE_ID, 1, webhook_id=None)
    message.author.bot = from_bot
    raw_message.cached_message = message

    await cog.on_raw_message_delete(raw_message)

    assert not await is_deleted(post)


async def test_cached_webhook_message_is_marked(
    cog: RoleplayCog,
    raw_message: discord.RawMessageDeleteEvent,
    save_post: PostSaver,
    vguild: VGuild,
):
    """A cached webhook message may be a Rolepost."""
    post = await save_post()
    raw_message.cached_message = cached_message(MESSAGE_ID, WEBHOOK_ID, webhook_id=WEBHOOK_ID)

    await cog.on_raw_message_delete(raw_message)

    assert await is_deleted(post)


# Test on_raw_bulk_message_delete


async def test_bulk_delete_marks_possible_roleposts(
    cog: RoleplayCog, mock_rp_posts: AsyncMock, vguild: VGuild
):
    """Bulk deletions mark cached webhook messages and uncached messages, but not
    cached messages from users."""
    webhook_message = cached_message(1, WEBHOOK_ID, webhook_id=WEBHOOK_ID)
    user_message = cached_message(2, 100, webhook_id=None)

    await cog.on_raw_bulk_message_delete(bulk_event(webhook_message, user_message, ids={1, 2, 3}))

    updates = mock_rp_posts.bulk_write.await_args.args[0]
    assert sorted(update._filter["message_id"] for update in updates) == [1, 3]
    for update in updates:
        assert update._doc["$set"]["deleted"] is True


async def test_bulk_delete_of_only_user_messages(
    cog: RoleplayCog, deletion_channel: MockChannel, mock_rp_posts: AsyncMock
):
    """With nothing that could be a Rolepost, nothing is marked or reported."""
    message = cached_message(1, 100, webhook_id=None)

    await cog.on_raw_bulk_message_delete(bulk_event(message, ids={1}))

    mock_rp_posts.bulk_write.assert_not_awaited()
    deletion_channel.send.assert_not_awaited()


async def test_bulk_delete_sends_spaced_notices(
    cog: RoleplayCog,
    deletion_channel: MockChannel,
    mock_rp_posts: AsyncMock,
    save_post: PostSaver,
    deletion_guild: VGuild,
):
    """Each purged post gets a full notice, oldest first, with a delay between them."""
    await save_post(1, "Newest", date=datetime(2026, 1, 3))
    await save_post(2, "Oldest", date=datetime(2026, 1, 1))
    await save_post(3, "Middle", date=datetime(2026, 1, 2))
    await save_post(4, "Not purged")
    message = cached_message(1, WEBHOOK_ID, webhook_id=WEBHOOK_ID)

    with patch.object(roleplay_module.asyncio, "sleep", new_callable=AsyncMock) as sleep:
        await cog.on_raw_bulk_message_delete(bulk_event(message, ids={1, 2, 3}))

    embeds = [call.kwargs["embed"] for call in deletion_channel.send.await_args_list]
    assert [embed.title for embed in embeds] == ["Post Deleted"] * 3
    assert [embed.description.splitlines()[-1] for embed in embeds] == [
        "Oldest",
        "Middle",
        "Newest",
    ]
    assert sleep.await_args_list == [call(roleplay_module.NOTICE_DELAY)] * 2


async def test_bulk_delete_of_one_post_has_no_delay(
    cog: RoleplayCog,
    deletion_channel: MockChannel,
    mock_rp_posts: AsyncMock,
    save_post: PostSaver,
    deletion_guild: VGuild,
):
    """The delay only goes between notices."""
    await save_post(1)

    with patch.object(roleplay_module.asyncio, "sleep", new_callable=AsyncMock) as sleep:
        await cog.on_raw_bulk_message_delete(bulk_event(ids={1}))

    deletion_channel.send.assert_awaited_once()
    sleep.assert_not_awaited()


async def test_bulk_delete_without_roleposts_sends_nothing(
    cog: RoleplayCog,
    deletion_channel: MockChannel,
    mock_rp_posts: AsyncMock,
    save_post: PostSaver,
    deletion_guild: VGuild,
):
    """Uncached messages that weren't Roleposts don't produce a notice."""
    await cog.on_raw_bulk_message_delete(bulk_event(ids={1}))

    mock_rp_posts.bulk_write.assert_awaited_once()
    deletion_channel.send.assert_not_awaited()


async def test_bulk_delete_without_deletion_channel(
    cog: RoleplayCog,
    deletion_channel: MockChannel,
    mock_rp_posts: AsyncMock,
    vguild: VGuild,
):
    """Without a deletion channel, posts are marked and there's nothing to look up."""
    with patch.object(RPPost, "find") as find:
        await cog.on_raw_bulk_message_delete(bulk_event(ids={1}))

    mock_rp_posts.bulk_write.assert_awaited_once()
    find.assert_not_called()
    deletion_channel.send.assert_not_awaited()


async def test_bulk_delete_outside_a_guild(
    cog: RoleplayCog, mock_bot: MockBot, mock_rp_posts: AsyncMock
):
    """A bulk deletion with no guild has no deletion channel to look up."""
    payload = bulk_event(ids={1})
    payload.guild_id = None

    await cog.on_raw_bulk_message_delete(payload)

    mock_rp_posts.bulk_write.assert_awaited_once()
    mock_bot.get_or_fetch_guild.assert_not_awaited()


@pytest.mark.parametrize("error", [discord.Forbidden, discord.HTTPException])
async def test_bulk_notice_failure_is_ignored(
    cog: RoleplayCog,
    deletion_channel: MockChannel,
    mock_rp_posts: AsyncMock,
    save_post: PostSaver,
    deletion_guild: VGuild,
    error: type[discord.HTTPException],
):
    """A broken deletion channel doesn't raise an error."""
    await save_post(1)
    deletion_channel.send.side_effect = http_error(error)

    await cog.on_raw_bulk_message_delete(bulk_event(ids={1}))

    deletion_channel.send.assert_awaited_once()


# Test on_guild_channel_delete


async def test_channel_delete_marks_its_roleposts(cog: RoleplayCog, mock_rp_posts: AsyncMock):
    """Deleting a channel marks every Rolepost in it as deleted."""
    channel = MagicMock(spec=discord.TextChannel, id=4321)
    channel.name = "scene"

    await cog.on_guild_channel_delete(channel)

    query, update = mock_rp_posts.update_many.await_args.args
    assert query == {"channel": 4321}
    assert update["$set"]["deleted"] is True
