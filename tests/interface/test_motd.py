"""Tests for interface/motd.py's post-command MOTD."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import interface.motd as motd_module
from bot import InconnuBot
from ctx import AppCtx
from interface.motd import MotDCog

type MockCtx = MagicMock


def make_ctx(command: str = "vr") -> MockCtx:
    """A command context for the given command."""
    ctx = MagicMock(spec=AppCtx)
    ctx.command = MagicMock(spec=discord.SlashCommand)
    ctx.command.qualified_name = command
    ctx.user = MagicMock(spec=discord.Member)
    ctx.user.configure_mock(id=1, name="User")
    return ctx


@pytest.fixture
def cog() -> MotDCog:
    """A MotDCog on a mock bot with an MOTD that nobody has seen."""
    bot = MagicMock(spec=InconnuBot)
    bot.motd = discord.Embed(title="News")
    bot.motd_given = set()
    return MotDCog(bot)


@pytest.fixture
async def mock_cmd_replace_respond() -> AsyncGenerator[AsyncMock]:
    """cmd_replace_respond(), patched, with the pre-send sleep skipped."""
    with (
        patch.object(motd_module, "cmd_replace_respond", new_callable=AsyncMock) as mock,
        patch.object(motd_module.asyncio, "sleep", new_callable=AsyncMock),
    ):
        yield mock


async def test_motd_shown_once(cog: MotDCog, mock_cmd_replace_respond: AsyncMock):
    """Each user sees the MOTD only once."""
    ctx = make_ctx()
    await cog.on_application_command(ctx)
    await cog.on_application_command(ctx)

    mock_cmd_replace_respond.assert_awaited_once_with(ctx, embed=cog.bot.motd, ephemeral=True)
    assert cog.bot.motd_given == {ctx.user.id}


@pytest.mark.parametrize("command", ["motd", "announce"])
async def test_motd_not_shown_for_exempt_command(
    cog: MotDCog, mock_cmd_replace_respond: AsyncMock, command: str
):
    """The MOTD commands don't show the MOTD."""
    await cog.on_application_command(make_ctx(command))

    mock_cmd_replace_respond.assert_not_awaited()


async def test_motd_not_set(cog: MotDCog, mock_cmd_replace_respond: AsyncMock):
    """Nothing is shown without an MOTD."""
    cog.bot.motd = None
    await cog.on_application_command(make_ctx())

    mock_cmd_replace_respond.assert_not_awaited()


async def test_motd_failure_not_recorded(cog: MotDCog, mock_cmd_replace_respond: AsyncMock):
    """A user whose MOTD couldn't be sent will get it next time."""
    mock_cmd_replace_respond.side_effect = discord.HTTPException(MagicMock(status=500), "Failed")
    await cog.on_application_command(make_ctx())

    assert cog.bot.motd_given == set()
