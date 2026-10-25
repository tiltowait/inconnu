"""Tests for inconnu/vr/parse.py mention stringification."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import discord
import pytest

from ctx import AppCtx
from inconnu.vr.parse import stringify_mentions

MEMBER_ID = 280000000000000001
CHANNEL_ID = 280000000000000002
THREAD_ID = 280000000000000003
UNKNOWN_ID = 280000000000000100


def not_found() -> discord.NotFound:
    """A NotFound error, as raised by fetch_member()."""
    response = MagicMock(spec=aiohttp.ClientResponse)
    response.status = 404
    response.reason = "Not Found"
    return discord.NotFound(response, "Unknown Member")


def make_member(name: str) -> discord.Member:
    """A member with the given display name."""
    member = MagicMock(spec=discord.Member)
    member.display_name = name
    return member


@pytest.fixture
def member() -> discord.Member:
    """A guild member who is in the cache."""
    return make_member("Nadea")


@pytest.fixture
def channel() -> discord.TextChannel:
    """A guild channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = "general"
    return channel


@pytest.fixture
def thread() -> discord.Thread:
    """A thread in the guild."""
    thread = MagicMock(spec=discord.Thread)
    thread.name = "scene-1"
    return thread


@pytest.fixture
def ctx(member: discord.Member, channel: discord.TextChannel, thread: discord.Thread) -> AppCtx:
    """A guild context whose caches contain one member, one channel, and one thread."""
    guild = MagicMock(spec=discord.Guild)
    guild.get_member.side_effect = lambda id: member if id == MEMBER_ID else None
    guild.fetch_member = AsyncMock(side_effect=not_found())
    guild.get_channel_or_thread.side_effect = {CHANNEL_ID: channel, THREAD_ID: thread}.get

    ctx = MagicMock(spec=AppCtx)
    ctx.guild = guild
    ctx.bot = MagicMock(spec=discord.Bot)
    return ctx


@pytest.fixture
def dm_ctx() -> AppCtx:
    """A DM context. The bot can see one user, whose global name differs from
    their server nickname."""
    user = MagicMock(spec=discord.User)
    user.display_name = "tiltowait"

    ctx = MagicMock(spec=AppCtx)
    ctx.guild = None
    ctx.bot = MagicMock(spec=discord.Bot)
    ctx.bot.get_user.side_effect = lambda id: user if id == MEMBER_ID else None
    return ctx


@pytest.mark.parametrize("sentence", [None, ""])
async def test_empty(ctx: AppCtx, sentence: str | None):
    """Empty comments become None."""
    assert await stringify_mentions(ctx, sentence) is None


async def test_no_mentions(ctx: AppCtx):
    """Comments without mentions only have their whitespace collapsed."""
    assert await stringify_mentions(ctx, "  a   comment \n here ") == "a comment here"


@pytest.mark.parametrize("mention", [f"<@{MEMBER_ID}>", f"<@!{MEMBER_ID}>"])
async def test_cached_member(ctx: AppCtx, mention: str):
    """Cached members are replaced with their display names."""
    assert await stringify_mentions(ctx, f"Biting {mention}") == "Biting @Nadea"


async def test_uncached_member_is_fetched(ctx: AppCtx):
    """Members missing from the cache are fetched."""
    guild = ctx.guild
    assert guild is not None
    fetch = AsyncMock(return_value=make_member("Ozzy"))
    guild.fetch_member = fetch

    assert await stringify_mentions(ctx, f"Biting <@{UNKNOWN_ID}>") == "Biting @Ozzy"
    fetch.assert_awaited_once_with(UNKNOWN_ID)


async def test_unknown_member_is_left_raw(ctx: AppCtx):
    """Members that can't be found are left as raw mentions."""
    sentence = f"Biting <@{UNKNOWN_ID}>"
    assert await stringify_mentions(ctx, sentence) == sentence


async def test_channel(ctx: AppCtx):
    """Channels are replaced with their names."""
    assert await stringify_mentions(ctx, f"Meet in <#{CHANNEL_ID}>") == "Meet in #general"


async def test_thread(ctx: AppCtx):
    """Threads are replaced with their names."""
    assert await stringify_mentions(ctx, f"Meet in <#{THREAD_ID}>") == "Meet in #scene-1"


async def test_unknown_channel_is_left_raw(ctx: AppCtx):
    """Channels that can't be found are left as raw mentions."""
    sentence = f"Meet in <#{UNKNOWN_ID}>"
    assert await stringify_mentions(ctx, sentence) == sentence


async def test_repeated_mention(ctx: AppCtx):
    """Repeated mentions are looked up once and all replaced."""
    guild = ctx.guild
    assert guild is not None
    result = await stringify_mentions(ctx, f"<@{MEMBER_ID}> and <@{MEMBER_ID}>")

    assert result == "@Nadea and @Nadea"
    cast(MagicMock, guild.get_member).assert_called_once_with(MEMBER_ID)


async def test_lookups_stop_after_three_failures(ctx: AppCtx):
    """After three failed lookups, the rest of the mentions are left alone."""
    guild = ctx.guild
    assert guild is not None
    fetch = AsyncMock(side_effect=not_found())
    guild.fetch_member = fetch
    sentence = " ".join(f"<@{UNKNOWN_ID + n}>" for n in range(5))

    assert await stringify_mentions(ctx, sentence) == sentence
    assert fetch.await_count == 3


async def test_dm_user(dm_ctx: AppCtx):
    """In DMs, users are shown by their global display name."""
    assert await stringify_mentions(dm_ctx, f"Hi <@{MEMBER_ID}>") == "Hi @tiltowait"


async def test_dm_channel_is_left_raw(dm_ctx: AppCtx):
    """In DMs, there's no guild to find channels in."""
    sentence = f"Meet in <#{CHANNEL_ID}>"
    assert await stringify_mentions(dm_ctx, sentence) == sentence
