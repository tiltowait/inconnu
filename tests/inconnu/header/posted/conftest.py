"""Shared fixtures for inconnu.header.posted tests."""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest


@pytest.fixture
def bot_user() -> discord.User:
    """The bot's user identity."""
    user = MagicMock(spec=discord.User)
    user.id = 999
    return user


@pytest.fixture
def owner_user() -> discord.Member:
    """The header owner."""
    user = MagicMock(spec=discord.Member)
    user.id = 100
    user.name = "owner"
    return user


@pytest.fixture
def other_user() -> discord.Member:
    """A non-owner user."""
    user = MagicMock(spec=discord.Member)
    user.id = 200
    user.name = "intruder"
    return user


@pytest.fixture
def webhook() -> discord.Webhook:
    """A resolved webhook (AsyncMock so async methods like delete_message work)."""
    wh = AsyncMock(spec=discord.Webhook)
    wh.id = 888
    return wh


@pytest.fixture
def header_record(owner_user: discord.Member) -> dict:
    """A database header record."""
    return {"character": {"user": owner_user.id}, "message": 12345}


@pytest.fixture
def ctx(owner_user: discord.Member, bot_user: discord.User, webhook: discord.Webhook) -> AsyncMock:
    """A minimal AppCtx mock with prep_webhook returning a webhook."""
    ctx = AsyncMock()
    ctx.user = owner_user
    ctx.bot = MagicMock()
    ctx.bot.user = bot_user
    ctx.bot.prep_webhook = AsyncMock(return_value=webhook)
    ctx.channel = MagicMock(spec=discord.TextChannel)
    ctx.channel.name = "test-channel"
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.name = "Test Guild"
    return ctx
