"""Tests for utils.cmdreplace."""

from collections.abc import Iterator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord.state import ConnectionState

import ui
from bot import InconnuBot
from ctx import AppCtx, AppInteraction
from tests.mocks import MockMember
from utils.cmdreplace import cmd_replace_respond

MENTION = "</help:1>"

type MockBot = MagicMock


@pytest.fixture
def bot() -> MockBot:
    """A bot that knows every command."""
    mock = MagicMock(spec=InconnuBot)
    mock.cmd_mention.return_value = MENTION
    return mock


@pytest.fixture
def member() -> MockMember:
    """The user who triggered the interaction."""
    mock = MagicMock(spec=discord.Member)
    mock.display_name = "Nadea"
    return mock


@pytest.fixture
def mock_respond() -> Iterator[AsyncMock]:
    """Patch responding to an interaction."""
    with patch.object(discord.Interaction, "respond", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def interaction(bot: MockBot, member: MockMember) -> AppInteraction:
    """A real interaction, as views and modals get. Unlike a mock, it has no
    attributes that py-cord doesn't give it."""
    inter = object.__new__(discord.Interaction)
    inter._state = MagicMock(spec=ConnectionState)
    inter._state._get_client = MagicMock(return_value=bot)  # Set by __init__
    inter.user = member
    return cast(AppInteraction, inter)


async def test_respond_with_interaction(interaction: AppInteraction, mock_respond: AsyncMock):
    """Commands are mentioned when responding through an interaction."""
    await cmd_replace_respond(interaction, "See `/help`.")

    mock_respond.assert_awaited_once_with(f"See {MENTION}.")


async def test_respond_with_ctx(bot: MockBot):
    """Commands are mentioned when responding through an AppCtx."""
    ctx = AppCtx(bot, MagicMock(spec=discord.Interaction))

    with patch.object(AppCtx, "respond", new_callable=AsyncMock) as respond:
        await cmd_replace_respond(ctx, "See `/help`.")

    respond.assert_awaited_once_with(f"See {MENTION}.")


async def test_embed_commands_mentioned(interaction: AppInteraction, mock_respond: AsyncMock):
    """Commands in an embed are mentioned too."""
    embed = discord.Embed(description="See `/help`.")

    await cmd_replace_respond(interaction, embed=embed)

    assert embed.description == f"See {MENTION}."


async def test_error_embed_from_interaction(interaction: AppInteraction, mock_respond: AsyncMock):
    """Modals and views can show error embeds, privately by default."""
    await ui.embeds.error(interaction, "Bad input.")

    mock_respond.assert_awaited_once()
    kwargs = mock_respond.call_args.kwargs
    assert kwargs["embed"].description == "Bad input."
    assert kwargs["ephemeral"] is True
