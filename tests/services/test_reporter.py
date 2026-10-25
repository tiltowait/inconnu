"""Tests for services/reporter.py's update channel reports."""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import discord

from ctx import AppCtx
from services.reporter import character_update


def make_ctx() -> AppCtx:
    """A context in a guild."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild = MagicMock(spec=discord.Guild)
    return ctx


async def test_character_update_returns_sent_message():
    """The sent report is returned, so callers can edit it later."""
    channel = AsyncMock(spec=discord.TextChannel)
    embed = discord.Embed(title="Roll")
    with patch("services.settings.update_channel", new_callable=AsyncMock, return_value=channel):
        sent = await character_update(
            ctx=make_ctx(), character=None, title="Hidden roll", message="Hi", embed=embed
        )

    channel.send.assert_awaited_once_with("Hi", embed=embed, allowed_mentions=ANY)
    assert sent is channel.send.return_value


async def test_character_update_without_channel():
    """Nothing is sent without an update channel."""
    with patch("services.settings.update_channel", new_callable=AsyncMock, return_value=None):
        sent = await character_update(ctx=make_ctx(), character=None, title="T", message="M")

    assert sent is None


async def test_character_update_forbidden():
    """Without permission to post, nothing is returned."""
    channel = AsyncMock(spec=discord.TextChannel)
    channel.name = "updates"
    channel.guild = MagicMock(spec=discord.Guild)
    channel.send.side_effect = discord.Forbidden(MagicMock(status=403), "Missing Access")
    embed = discord.Embed(title="Roll")
    with patch("services.settings.update_channel", new_callable=AsyncMock, return_value=channel):
        sent = await character_update(
            ctx=make_ctx(), character=None, title="T", message="M", embed=embed
        )

    assert sent is None
