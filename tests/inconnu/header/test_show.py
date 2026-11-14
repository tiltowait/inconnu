"""Tests for inconnu/header/show.py's header registration."""

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import discord
import pytest
from beanie import PydanticObjectId

import errors
from ctx import AppCtx
from inconnu.header.show import register_header
from models import PostedHeader, VChar

type MockChannel = MagicMock
type MockCtx = MagicMock

CHANNEL_ID = 1
THREAD_ID = 2
GUILD_ID = 10
USER_ID = 20
MESSAGE_ID = 30


@pytest.fixture(autouse=True)
async def clear_headers() -> AsyncGenerator[None]:
    """Start and end with no header records."""
    await PostedHeader.delete_all()
    yield
    await PostedHeader.delete_all()


def ctx_in(channel: MockChannel) -> MockCtx:
    """A command context in the given channel."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild = MagicMock(spec=discord.Guild, id=GUILD_ID)
    ctx.user = MagicMock(spec=discord.Member, id=USER_ID)
    ctx.channel = channel
    return ctx


async def register(channel: MockChannel, spc=False) -> PostedHeader:
    """Register a header posted in the channel, returning its stored record."""
    character = MagicMock(spec=VChar, id=PydanticObjectId(), is_spc=spc)
    message = MagicMock(spec=discord.Message, id=MESSAGE_ID)
    await register_header(ctx_in(channel), message, character)

    record = await PostedHeader.find_one(PostedHeader.message == MESSAGE_ID)
    assert record is not None
    return record


async def test_register_in_channel():
    """A channel's header records its owner and has no parent."""
    record = await register(MagicMock(spec=discord.TextChannel, id=CHANNEL_ID))

    assert record.channel == CHANNEL_ID
    assert record.parent is None
    assert (record.character.guild, record.character.user) == (GUILD_ID, USER_ID)
    assert record.character.spc is False


async def test_register_in_thread():
    """A thread's header records the thread and its parent."""
    thread = MagicMock(spec=discord.Thread, id=THREAD_ID, parent_id=CHANNEL_ID)
    record = await register(thread)

    assert (record.channel, record.parent) == (THREAD_ID, CHANNEL_ID)


async def test_register_spc():
    """An SPC's header is marked as one."""
    record = await register(MagicMock(spec=discord.TextChannel, id=CHANNEL_ID), spc=True)

    assert record.character.spc is True


async def test_unsaved_character_rejected():
    """A character without an ID can't own a header."""
    character = MagicMock(spec=VChar, id=None, is_spc=False)
    character.name = "Nameless"
    message = MagicMock(spec=discord.Message, id=MESSAGE_ID)
    channel = MagicMock(spec=discord.TextChannel, id=CHANNEL_ID)

    with pytest.raises(errors.CharacterError, match="Nameless"):
        await register_header(ctx_in(channel), message, character)

    assert await PostedHeader.find_one(PostedHeader.message == MESSAGE_ID) is None
