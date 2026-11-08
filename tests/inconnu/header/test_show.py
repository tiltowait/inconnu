"""Tests for inconnu/header/show.py's header registration."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from beanie import PydanticObjectId
from pymongo.asynchronous.collection import AsyncCollection

import db
from ctx import AppCtx
from inconnu.header.show import register_header
from models import VChar

type MockChannel = MagicMock
type MockCollection = AsyncMock
type MockCtx = MagicMock

CHANNEL_ID = 1
THREAD_ID = 2


@pytest.fixture
def headers() -> Generator[MockCollection]:
    """The header collection."""
    collection = AsyncMock(spec=AsyncCollection)
    with patch.object(db, "headers", collection):
        yield collection


def ctx_in(channel: MockChannel) -> MockCtx:
    """A command context in the given channel."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild = MagicMock(spec=discord.Guild, id=10)
    ctx.user = MagicMock(spec=discord.Member, id=20)
    ctx.channel = channel
    return ctx


async def register(channel: MockChannel, headers: MockCollection) -> dict:
    """Register a header posted in the channel, returning its record."""
    character = MagicMock(spec=VChar, id=PydanticObjectId(), is_spc=False)
    message = MagicMock(spec=discord.Message, id=30)
    await register_header(ctx_in(channel), message, character)
    return headers.insert_one.await_args.args[0]


async def test_register_in_channel(headers: MockCollection):
    """A channel's header has no parent."""
    record = await register(MagicMock(spec=discord.TextChannel, id=CHANNEL_ID), headers)

    assert record["channel"] == CHANNEL_ID
    assert "parent" not in record


async def test_register_in_thread(headers: MockCollection):
    """A thread's header records the thread and its parent."""
    thread = MagicMock(spec=discord.Thread, id=THREAD_ID, parent_id=CHANNEL_ID)
    record = await register(thread, headers)

    assert (record["channel"], record["parent"]) == (THREAD_ID, CHANNEL_ID)
