"""Tests for services/reporter.py's update channel reports."""

from typing import cast
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import discord

from ctx import AppCtx
from services.reporter import post_update
from tests.characters import gen_char


def make_ctx() -> AppCtx:
    """A context in a guild."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild = MagicMock(spec=discord.Guild)
    return ctx


async def test_post_update_returns_sent_message():
    """The sent report is returned, so callers can edit it later."""
    channel = AsyncMock(spec=discord.TextChannel)
    embed = discord.Embed(title="Roll")
    with patch("services.settings.update_channel", new_callable=AsyncMock, return_value=channel):
        sent = await post_update(
            ctx=make_ctx(), character=None, title="Hidden roll", message="Hi", embed=embed
        )

    channel.send.assert_awaited_once_with("Hi", embed=embed, allowed_mentions=ANY)
    assert sent is channel.send.return_value


async def test_post_update_without_channel():
    """Nothing is sent without an update channel."""
    with patch("services.settings.update_channel", new_callable=AsyncMock, return_value=None):
        sent = await post_update(ctx=make_ctx(), character=None, title="T", message="M")

    assert sent is None


async def test_post_update_forbidden():
    """Without permission to post, nothing is returned."""
    channel = AsyncMock(spec=discord.TextChannel)
    channel.name = "updates"
    channel.guild = MagicMock(spec=discord.Guild)
    channel.send.side_effect = discord.Forbidden(MagicMock(status=403), "Missing Access")
    embed = discord.Embed(title="Roll")
    with patch("services.settings.update_channel", new_callable=AsyncMock, return_value=channel):
        sent = await post_update(
            ctx=make_ctx(), character=None, title="T", message="M", embed=embed
        )

    assert sent is None


async def test_post_update_in_dm():
    """DMs have no update channel."""
    ctx = make_ctx()
    cast(MagicMock, ctx).guild = None
    with patch("services.settings.update_channel", new_callable=AsyncMock) as mock_channel:
        sent = await post_update(ctx=ctx, character=None, title="T", message="M")

    assert sent is None
    mock_channel.assert_not_awaited()


async def test_post_update_builds_embed():
    """Without an embed, one is built from the update, linking to msg."""
    ctx = make_ctx()
    user = MagicMock(spec=discord.Member)
    user.guild_avatar = "https://example.com/avatar.png"
    cast(MagicMock, ctx).user = user
    character = gen_char("vampire")
    msg = MagicMock(spec=discord.Message)
    msg.jump_url = "https://discord.com/channels/1/2/3"
    channel = AsyncMock(spec=discord.TextChannel)
    with patch("services.settings.update_channel", new_callable=AsyncMock, return_value=channel):
        await post_update(
            ctx=ctx, character=character, title="Rouse Check", message="M", msg=msg, color=0x123
        )

    assert channel.send.await_args is not None
    content = channel.send.await_args.args[0]
    embed: discord.Embed = channel.send.await_args.kwargs["embed"]
    assert embed.author is not None
    assert content == ""
    assert (embed.title, embed.description, embed.url) == ("Rouse Check", "M", msg.jump_url)
    assert embed.colour == discord.Colour(0x123)
    assert embed.author.name == character.name
