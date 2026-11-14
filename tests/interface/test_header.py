"""Tests for interface/header.py's listeners."""

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import discord
import pytest
from beanie import PydanticObjectId

from bot import InconnuBot
from interface.header import HeaderCog
from models import PostedHeader
from models.postedheader import HeaderOwner
from services.webhooks import WebhookCache

CHANNEL_ID = 4321
THREAD_ID = 8765
OTHER_CHANNEL_ID = 1111


@pytest.fixture(autouse=True)
async def clear_headers() -> AsyncGenerator[None]:
    """Start and end with no header records."""
    await PostedHeader.delete_all()
    yield
    await PostedHeader.delete_all()


@pytest.fixture
def cog() -> HeaderCog:
    """The header cog."""
    bot = MagicMock(spec=InconnuBot)
    bot.webhook_cache = MagicMock(spec=WebhookCache, webhook_ids=set())
    return HeaderCog(bot)


async def add_header(message: int, channel: int, parent: int | None = None):
    """Store a header record."""
    owner = HeaderOwner(guild=1, user=2, charid=PydanticObjectId(), spc=False)
    header = PostedHeader(
        character=owner,
        channel=channel,
        message=message,
        parent=parent,
        timestamp=discord.utils.utcnow(),
    )
    await header.insert()


async def remaining() -> set[int]:
    """The message IDs of the remaining header records."""
    return {header.message async for header in PostedHeader.find_all()}


async def test_message_delete_removes_its_header(cog: HeaderCog):
    """Deleting an uncached message removes its header record."""
    await add_header(1, CHANNEL_ID)
    await add_header(2, CHANNEL_ID)
    payload = MagicMock(spec=discord.RawMessageDeleteEvent, message_id=1, cached_message=None)

    await cog.on_raw_message_delete(payload)

    assert await remaining() == {2}


async def test_bulk_delete_removes_their_headers(cog: HeaderCog):
    """Bulk-deleting uncached messages removes their header records."""
    for message in (1, 2, 3):
        await add_header(message, CHANNEL_ID)
    payload = MagicMock(
        spec=discord.RawBulkMessageDeleteEvent, message_ids={1, 3}, cached_messages=[]
    )

    await cog.on_raw_bulk_message_delete(payload)

    assert await remaining() == {2}


async def test_thread_delete_removes_its_headers(cog: HeaderCog):
    """Deleting a thread removes its header records, not its parent's."""
    await add_header(1, CHANNEL_ID)
    await add_header(2, THREAD_ID, parent=CHANNEL_ID)
    payload = MagicMock(spec=discord.RawThreadDeleteEvent, thread_id=THREAD_ID)

    await cog.on_raw_thread_delete(payload)

    assert await remaining() == {1}


async def test_channel_delete_removes_its_headers(cog: HeaderCog):
    """Deleting a channel removes its header records and its threads'."""
    await add_header(1, CHANNEL_ID)
    await add_header(2, THREAD_ID, parent=CHANNEL_ID)
    await add_header(3, OTHER_CHANNEL_ID)
    channel = MagicMock(spec=discord.TextChannel, id=CHANNEL_ID)
    channel.name = "scene"

    await cog.on_guild_channel_delete(channel)

    assert await remaining() == {3}
