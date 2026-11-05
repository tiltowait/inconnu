"""Tests for interface/errorlistener.py's error routing."""

import asyncio
from collections.abc import Iterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot import InconnuBot
from ctx import AppCtx
from interface.errorlistener import ErrorListener

type MockInteraction = MagicMock


@pytest.fixture
def bot() -> discord.Bot:
    """A plain bot with only the ErrorListener loaded."""
    bot = discord.Bot()
    bot.add_cog(ErrorListener(cast(InconnuBot, bot)))
    return bot


@pytest.fixture
def cog(bot: discord.Bot) -> ErrorListener:
    """The bot's ErrorListener."""
    return cast(ErrorListener, bot.get_cog("ErrorListener"))


@pytest.fixture
def mock_report(cog: ErrorListener) -> Iterator[AsyncMock]:
    """The cog's report_error(), patched."""
    with patch.object(cog.reporter, "report_error", new_callable=AsyncMock) as mock:
        yield mock


def make_interaction(bot: discord.Bot) -> MockInteraction:
    """A component interaction from the bot."""
    inter = MagicMock(spec=discord.Interaction)
    inter.client = bot
    return inter


async def drain(bot: discord.Bot):
    """Wait for the bot's dispatched event handlers to finish."""
    await asyncio.gather(*bot._tasks)


async def test_command_error_reported(bot: discord.Bot, mock_report: AsyncMock):
    """A command error dispatched by the bot reaches the reporter."""
    ctx = MagicMock(spec=AppCtx)
    error = discord.DiscordException("boom")

    bot.dispatch("application_command_error", ctx, error)
    await drain(bot)

    mock_report.assert_awaited_once_with(ctx, error)


async def test_view_error_reported(bot: discord.Bot, mock_report: AsyncMock):
    """A view's default on_error dispatches to the reporter."""
    view = discord.ui.View()
    inter = make_interaction(bot)
    error = ValueError("boom")

    await view.on_error(error, MagicMock(spec=discord.ui.Button), inter)
    await drain(bot)

    mock_report.assert_awaited_once_with(inter, error)


async def test_modal_error_reported(bot: discord.Bot, mock_report: AsyncMock):
    """A modal's default on_error dispatches to the reporter."""
    modal = discord.ui.Modal(title="Test")
    inter = make_interaction(bot)
    error = ValueError("boom")

    await modal.on_error(error, inter)
    await drain(bot)

    mock_report.assert_awaited_once_with(inter, error)
