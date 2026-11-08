"""Tests for interface/header.py's listeners."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
from pymongo.asynchronous.collection import AsyncCollection

import db
from bot import InconnuBot
from interface.header import HeaderCog


async def test_thread_delete_removes_its_headers():
    """Deleting a thread removes its header records."""
    cog = HeaderCog(MagicMock(spec=InconnuBot))
    payload = MagicMock(spec=discord.RawThreadDeleteEvent, thread_id=8765)
    headers = AsyncMock(spec=AsyncCollection)

    with patch.object(db, "headers", headers):
        await cog.on_raw_thread_delete(payload)

    headers.delete_many.assert_awaited_once_with({"channel": 8765})


async def test_channel_delete_removes_its_headers():
    """Deleting a channel removes its header records and its threads'."""
    cog = HeaderCog(MagicMock(spec=InconnuBot))
    channel = MagicMock(spec=discord.TextChannel, id=4321)
    channel.name = "scene"
    headers = AsyncMock(spec=AsyncCollection)

    with patch.object(db, "headers", headers):
        await cog.on_guild_channel_delete(channel)

    headers.delete_many.assert_awaited_once_with({"$or": [{"channel": 4321}, {"parent": 4321}]})
