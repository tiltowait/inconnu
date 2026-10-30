"""Tests for bot event handlers and guild cache integration."""

from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import bot as bot_module
from bot import InconnuBot
from models import RPPost
from services import WebhookCache, guild_cache

# Fixtures


@pytest.fixture(autouse=True, scope="function")
async def setup_guild_cache():
    """Set up guild cache with in-memory database for each test."""
    guild_cache.location = "file::memory:?cache=shared"
    guild_cache._initialized = False
    guild_cache._refreshed = False

    await guild_cache.initialize()
    yield guild_cache

    if guild_cache.initialized:
        await guild_cache.close()


@pytest.fixture
def mock_bot():
    """Create a mock InconnuBot instance."""
    bot = MagicMock(spec=InconnuBot)
    bot.guilds = []
    return bot


def make_mock_guild(guild_id: int, name: str, members: list | None = None) -> MagicMock:
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = name
    guild.icon = None
    guild.chunked = True
    guild.members = members or []
    return guild


def make_mock_member(
    member_id: int, guild: discord.Guild | None, name: str = "Test User"
) -> MagicMock:
    """Create a mock Discord member."""
    member = MagicMock(spec=discord.Member)
    member.id = member_id
    member.guild = guild
    member.name = name
    member.display_name = name
    member.display_avatar.url = "http://avatar.png"
    member.guild_avatar = None
    return member


async def mark_cache_ready():
    """Mark cache as ready by calling refresh."""
    guild_cache._refreshed = True


# Cog loading


async def test_missing_cog_dir_raises(tmp_path: Path, monkeypatch):
    """A missing interface directory fails loudly instead of loading no cogs."""
    monkeypatch.setattr(bot_module, "__file__", str(tmp_path / "bot.py"))

    with pytest.raises(RuntimeError, match="No cogs found"):
        InconnuBot(intents=discord.Intents.none())


# Guild event tests


async def test_on_guild_join_before_ready(mock_bot):
    """Guild not added to cache before ready."""
    guild = make_mock_guild(1, "Test Guild")

    # Simulate on_guild_join before ready
    with (
        patch("inconnu.stats.guild_joined", new_callable=AsyncMock),
        patch.object(mock_bot, "_set_presence", new_callable=AsyncMock),
    ):
        await InconnuBot.on_guild_join(mock_bot, guild)

    # Cache should not have the guild
    cached_guild = await guild_cache.fetchguild(guild.id)
    assert cached_guild is None


async def test_on_guild_join_after_ready(mock_bot):
    """Guild added to cache after ready."""
    guild = make_mock_guild(1, "Test Guild", members=[make_mock_member(100, None, "Member 1")])
    guild.members[0].guild = guild  # Fix circular ref

    # Mark cache as ready
    await mark_cache_ready()

    # Simulate on_guild_join after ready
    with (
        patch("inconnu.stats.guild_joined", new_callable=AsyncMock),
        patch.object(mock_bot, "_set_presence", new_callable=AsyncMock),
    ):
        await InconnuBot.on_guild_join(mock_bot, guild)

    # Cache should have the guild
    cached_guild = await guild_cache.fetchguild(guild.id)
    assert cached_guild is not None
    assert cached_guild.id == guild.id
    assert cached_guild.name == guild.name


async def test_on_guild_remove_before_ready(mock_bot):
    """Guild removal is no-op when cache not ready (no pre-existing data)."""
    guild = make_mock_guild(1, "Test Guild", members=[make_mock_member(100, None, "Member 1")])
    guild.members[0].guild = guild

    # Don't populate cache, so ready() returns False
    # Cache is initialized but empty (member_count = 0, _refreshed = False)

    # Simulate on_guild_remove before ready
    with (
        patch("inconnu.stats.guild_left", new_callable=AsyncMock),
        patch.object(mock_bot, "_set_presence", new_callable=AsyncMock),
    ):
        await InconnuBot.on_guild_remove(mock_bot, guild)

    # Guild should not be in cache
    cached_guild = await guild_cache.fetchguild(guild.id)
    assert cached_guild is None


async def test_on_guild_remove_after_ready(mock_bot):
    """Guild removed from cache after ready."""
    guild = make_mock_guild(1, "Test Guild", members=[make_mock_member(100, None, "Member 1")])
    guild.members[0].guild = guild

    # Add guild to cache and mark ready
    await guild_cache.upsert_guilds(guild)
    await mark_cache_ready()

    # Simulate on_guild_remove after ready
    with (
        patch("inconnu.stats.guild_left", new_callable=AsyncMock),
        patch.object(mock_bot, "_set_presence", new_callable=AsyncMock),
    ):
        await InconnuBot.on_guild_remove(mock_bot, guild)

    # Guild should be removed from cache
    cached_guild = await guild_cache.fetchguild(guild.id)
    assert cached_guild is None


async def test_on_guild_update_before_ready(mock_bot):
    """Guild update is no-op when cache not ready."""
    guild_before = make_mock_guild(1, "Old Name", members=[make_mock_member(100, None, "Member 1")])
    guild_before.members[0].guild = guild_before
    guild_after = make_mock_guild(1, "New Name", members=[make_mock_member(100, None, "Member 1")])
    guild_after.members[0].guild = guild_after

    # Don't populate cache, so ready() returns False
    # Cache is initialized but empty (member_count = 0, _refreshed = False)

    # Simulate on_guild_update before ready (cache not refreshed yet)
    with patch("inconnu.stats.guild_renamed", new_callable=AsyncMock):
        await InconnuBot.on_guild_update(mock_bot, guild_before, guild_after)

    # Guild should not be in cache at all
    cached_guild = await guild_cache.fetchguild(guild_after.id)
    assert cached_guild is None


async def test_on_guild_update_after_ready(mock_bot):
    """Guild updated in cache after ready."""
    guild_before = make_mock_guild(1, "Old Name", members=[make_mock_member(100, None, "Member 1")])
    guild_before.members[0].guild = guild_before
    guild_after = make_mock_guild(1, "New Name", members=[make_mock_member(100, None, "Member 1")])
    guild_after.members[0].guild = guild_after

    # Add guild to cache with old name and mark ready
    await guild_cache.upsert_guilds(guild_before)
    await mark_cache_ready()

    # Simulate on_guild_update after ready
    with patch("inconnu.stats.guild_renamed", new_callable=AsyncMock):
        await InconnuBot.on_guild_update(mock_bot, guild_before, guild_after)

    # Cache should have new name
    cached_guild = await guild_cache.fetchguild(guild_after.id)
    assert cached_guild is not None
    assert cached_guild.name == "New Name"


# Member event tests


async def test_on_member_join_before_ready(mock_bot):
    """Member not added to cache before ready."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)

    # Simulate on_member_join before ready
    with patch("services.char_mgr.mark_active", new_callable=AsyncMock):
        await InconnuBot.on_member_join(mock_bot, member)

    # Member should not be in cache
    cached_member = await guild_cache.fetchmember(guild.id, member.id)
    assert cached_member is None


async def test_on_member_join_after_ready(mock_bot):
    """Member added to cache after ready."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)

    # Add guild to cache and mark ready
    await guild_cache.upsert_guilds(guild)
    await mark_cache_ready()

    # Simulate on_member_join after ready
    with patch("services.char_mgr.mark_active", new_callable=AsyncMock):
        await InconnuBot.on_member_join(mock_bot, member)

    # Member should be in cache
    cached_member = await guild_cache.fetchmember(guild.id, member.id)
    assert cached_member is not None
    assert cached_member.id == member.id


async def test_on_member_remove_before_ready(mock_bot):
    """Member removal is no-op when cache not ready (no pre-existing data)."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)

    # Don't populate cache, so ready() returns False
    # Cache is initialized but empty (member_count = 0, _refreshed = False)

    # Simulate on_member_remove before ready
    with patch("services.char_mgr.mark_inactive", new_callable=AsyncMock):
        await InconnuBot.on_member_remove(mock_bot, member)

    # Member should not be in cache
    cached_member = await guild_cache.fetchmember(guild.id, member.id)
    assert cached_member is None


async def test_on_member_remove_after_ready(mock_bot):
    """Member removed from cache after ready."""
    guild = make_mock_guild(1, "Test Guild")
    member = make_mock_member(100, guild)

    # Add guild and member to cache, mark ready
    await guild_cache.upsert_guilds(guild)
    await guild_cache.upsert_members(member)
    await mark_cache_ready()

    # Simulate on_member_remove after ready
    with patch("services.char_mgr.mark_inactive", new_callable=AsyncMock):
        await InconnuBot.on_member_remove(mock_bot, member)

    # Member should be removed from cache
    cached_member = await guild_cache.fetchmember(guild.id, member.id)
    assert cached_member is None


async def test_on_member_update_before_ready(mock_bot):
    """Member update is no-op when cache not ready."""
    guild = make_mock_guild(1, "Test Guild")
    member_before = make_mock_member(100, guild, "Old Name")
    member_after = make_mock_member(100, guild, "New Name")

    # Don't populate cache, so ready() returns False
    # Cache is initialized but empty (member_count = 0, _refreshed = False)

    # Simulate on_member_update before ready (cache not refreshed)
    await InconnuBot.on_member_update(mock_bot, member_before, member_after)

    # Member should not be in cache at all
    cached_member = await guild_cache.fetchmember(guild.id, member_after.id)
    assert cached_member is None


async def test_on_member_update_after_ready(mock_bot):
    """Member updated in cache after ready."""
    guild = make_mock_guild(1, "Test Guild")
    member_before = make_mock_member(100, guild, "Old Name")
    member_after = make_mock_member(100, guild, "New Name")

    # Add guild and member to cache, mark ready
    await guild_cache.upsert_guilds(guild)
    await guild_cache.upsert_members(member_before)
    await mark_cache_ready()

    # Simulate on_member_update after ready
    await InconnuBot.on_member_update(mock_bot, member_before, member_after)

    # Cache should have new name
    cached_member = await guild_cache.fetchmember(guild.id, member_after.id)
    assert cached_member is not None
    assert cached_member.name == "New Name"


# Rolepost reply pings

WEBHOOK_ID = 50
AUTHOR_ID = 200


def make_reply(
    *,
    bot_author: bool = False,
    reference: bool = True,
    resolved: bool = True,
    to_webhook: bool = True,
    mentions: list[int] | None = None,
) -> MagicMock:
    """A reply to a message, by default a resolved reply to one of our webhooks."""
    message = MagicMock(spec=discord.Message)
    message.author.bot = bot_author
    message.mentions = [MagicMock(spec=discord.Member, id=m) for m in mentions or []]
    message.reply = AsyncMock()

    if not reference:
        message.reference = None
        return message

    message.reference = MagicMock(spec=discord.MessageReference)
    message.reference.message_id = 10
    if resolved:
        replied_to = MagicMock(spec=discord.Message)
        replied_to.author.id = WEBHOOK_ID if to_webhook else WEBHOOK_ID + 1
        message.reference.resolved = replied_to
    else:
        message.reference.resolved = None

    return message


@pytest.fixture
def reply_bot(mock_bot: MagicMock) -> MagicMock:
    """A mock bot that knows our webhook and can fetch the Rolepost's author."""
    mock_bot.webhook_cache = MagicMock(spec=WebhookCache)
    mock_bot.webhook_cache.webhook_ids = {WEBHOOK_ID}
    author = MagicMock(spec=discord.User)
    author.configure_mock(id=AUTHOR_ID, mention=f"<@{AUTHOR_ID}>", name="Author")
    mock_bot.get_or_fetch_user = AsyncMock(return_value=author)
    return mock_bot


@pytest.fixture
async def mock_find_post() -> AsyncGenerator[AsyncMock, None]:
    """RPPost.find_one(), patched to return a Rolepost by AUTHOR_ID."""
    rp_post = MagicMock(spec=RPPost)
    rp_post.user = AUTHOR_ID
    with patch.object(RPPost, "find_one", new_callable=AsyncMock, return_value=rp_post) as mock:
        yield mock


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bot_author": True},
        {"reference": False},
        {"resolved": False},
        {"to_webhook": False},
    ],
)
async def test_on_message_ignored(reply_bot: MagicMock, mock_find_post: AsyncMock, kwargs: dict):
    """Messages that aren't user replies to our webhooks are ignored."""
    message = make_reply(**kwargs)
    await InconnuBot.on_message(reply_bot, message)

    mock_find_post.assert_not_awaited()
    message.reply.assert_not_awaited()


async def test_on_message_no_rolepost(reply_bot: MagicMock, mock_find_post: AsyncMock):
    """Replies to webhook messages that aren't Roleposts are ignored."""
    mock_find_post.return_value = None
    message = make_reply()
    await InconnuBot.on_message(reply_bot, message)

    mock_find_post.assert_awaited_once_with({"id_chain": 10})
    message.reply.assert_not_awaited()


async def test_on_message_author_already_mentioned(reply_bot: MagicMock, mock_find_post: AsyncMock):
    """No ping when the replier already pinged the Rolepost's author."""
    message = make_reply(mentions=[AUTHOR_ID])
    await InconnuBot.on_message(reply_bot, message)

    message.reply.assert_not_awaited()


async def test_on_message_pings_author(reply_bot: MagicMock, mock_find_post: AsyncMock):
    """Replies to a Rolepost ping its author."""
    message = make_reply(mentions=[AUTHOR_ID + 1])
    await InconnuBot.on_message(reply_bot, message)

    reply_bot.get_or_fetch_user.assert_awaited_once_with(AUTHOR_ID)
    message.reply.assert_awaited_once_with(f"<@{AUTHOR_ID}>", mention_author=False, delete_after=60)
