"""Tests for character/update/parse.py's help message."""

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from bot import InconnuBot
from ctx import AppCtx
from inconnu.character.update.parse import update_help


def make_bot() -> MagicMock:
    """A bot whose user is named Inconnu."""
    bot = MagicMock(spec=InconnuBot)
    bot.me = MagicMock(spec=discord.ClientUser)
    bot.me.configure_mock(display_name="Inconnu", avatar="https://example.com/avatar.png")
    return bot


def make_ctx() -> MagicMock:
    """A slash command context, as /help section:Characters passes."""
    ctx = MagicMock(spec=AppCtx)
    ctx.bot = ctx.client = make_bot()
    ctx.respond = AsyncMock()
    return ctx


def make_interaction() -> MagicMock:
    """A plain Interaction, as the persistent "Character Updater" help button passes."""
    inter = MagicMock(spec=discord.Interaction)
    inter.client = make_bot()
    inter.respond = AsyncMock()
    return inter


@pytest.mark.parametrize("make_invocation", [make_ctx, make_interaction])
async def test_update_help(make_invocation: Callable[[], MagicMock]):
    """The help shows from both slash commands and the help button."""
    invocation = make_invocation()
    await update_help(invocation)

    invocation.respond.assert_awaited_once()
    embed = invocation.respond.await_args.kwargs["embed"]
    assert embed.author.name == "Inconnu"
