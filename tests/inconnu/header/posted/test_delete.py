"""Tests for inconnu.header.posted.delete."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import errors
from inconnu.header.posted.delete import delete_header

_IS_APPROVED = "inconnu.header.posted.delete.is_approved_user"


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
    """A non-owner, non-admin user."""
    user = MagicMock(spec=discord.Member)
    user.id = 200
    user.name = "intruder"
    return user


@pytest.fixture
def webhook() -> discord.Webhook:
    """A resolved webhook."""
    wh = AsyncMock(spec=discord.Webhook)
    wh.id = 888
    return wh


@pytest.fixture
def header_record(owner_user: discord.Member) -> dict:
    """A database header record."""
    return {"character": {"user": owner_user.id}, "message": 12345}


@pytest.fixture
def bot_message(bot_user: discord.User) -> discord.Message:
    """A Discord message authored by the bot."""
    msg = AsyncMock(spec=discord.Message)
    msg.id = 12345
    msg.author = bot_user
    return msg


@pytest.fixture
def webhook_message(webhook: discord.Webhook) -> discord.Message:
    """A Discord message authored by a webhook."""
    msg = AsyncMock(spec=discord.Message)
    msg.id = 67890
    msg.author = MagicMock(spec=discord.User)
    msg.author.id = webhook.id
    return msg


@pytest.fixture
def random_message() -> discord.Message:
    """A message not from the bot or a webhook."""
    msg = AsyncMock(spec=discord.Message)
    msg.id = 11111
    msg.author = MagicMock(spec=discord.User)
    msg.author.id = 777
    return msg


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


@pytest.fixture
def ctx_no_webhook(ctx: AsyncMock) -> AsyncMock:
    """A ctx where prep_webhook raises WebhookError."""
    ctx.bot.prep_webhook = AsyncMock(side_effect=errors.WebhookError("No permissions"))
    return ctx


# --- Authorization: not a bot/webhook message ---


async def test_random_message_rejected(ctx: AsyncMock, random_message: discord.Message):
    """A message not from the bot or webhook is rejected."""
    await delete_header(ctx, random_message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "not an RP header" in args[0]
    assert kwargs["ephemeral"] is True


async def test_random_message_rejected_when_webhook_error(
    ctx_no_webhook: AsyncMock, random_message: discord.Message
):
    """Same rejection when prep_webhook raises WebhookError."""
    await delete_header(ctx_no_webhook, random_message)

    ctx_no_webhook.respond.assert_awaited_once()
    args, kwargs = ctx_no_webhook.respond.await_args
    assert "not an RP header" in args[0]


async def test_random_message_rejected_when_value_error(
    ctx: AsyncMock, random_message: discord.Message
):
    """Same rejection when prep_webhook raises ValueError (non-text channel)."""
    ctx.bot.prep_webhook = AsyncMock(side_effect=ValueError("Not a text channel"))

    await delete_header(ctx, random_message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "not an RP header" in args[0]


# --- Authorization: no db record ---


async def test_bot_message_no_record(ctx: AsyncMock, bot_message: discord.Message):
    """Bot message with no header record is rejected."""
    with patch("db.headers.find_one", new_callable=AsyncMock, return_value=None):
        await delete_header(ctx, bot_message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "not an RP header" in args[0]


async def test_webhook_message_no_record(ctx: AsyncMock, webhook_message: discord.Message):
    """Webhook message with no header record is rejected."""
    with patch("db.headers.find_one", new_callable=AsyncMock, return_value=None):
        await delete_header(ctx, webhook_message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "not an RP header" in args[0]


# --- Authorization: permission denied ---


async def test_non_owner_non_admin_rejected(
    ctx: AsyncMock,
    bot_message: discord.Message,
    other_user: discord.Member,
    header_record: dict,
):
    """A non-owner, non-admin user is rejected."""
    ctx.user = other_user

    with (
        patch("db.headers.find_one", new_callable=AsyncMock, return_value=header_record),
        patch(_IS_APPROVED, return_value=False),
    ):
        await delete_header(ctx, bot_message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "don't have permission" in args[0]
    assert kwargs["ephemeral"] is True


# --- Successful deletion ---


async def test_owner_deletes_bot_message(
    ctx: AsyncMock, bot_message: discord.Message, header_record: dict
):
    """Owner deletes their own bot-authored header via message.delete()."""
    with (
        patch("db.headers.find_one", new_callable=AsyncMock, return_value=header_record),
        patch(_IS_APPROVED, return_value=True),
    ):
        await delete_header(ctx, bot_message)

    bot_message.delete.assert_awaited_once()
    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "deleted" in args[0]
    assert kwargs["delete_after"] == 3


async def test_admin_deletes_header(
    ctx: AsyncMock,
    bot_message: discord.Message,
    other_user: discord.Member,
    header_record: dict,
):
    """An admin can delete another user's header."""
    ctx.user = other_user

    with (
        patch("db.headers.find_one", new_callable=AsyncMock, return_value=header_record),
        patch(_IS_APPROVED, return_value=True),
    ):
        await delete_header(ctx, bot_message)

    bot_message.delete.assert_awaited_once()
    ctx.respond.assert_awaited_once()
    args, _ = ctx.respond.await_args
    assert "deleted" in args[0]


# --- Deletion routing ---


async def test_bot_message_uses_message_delete(
    ctx: AsyncMock, bot_message: discord.Message, webhook: discord.Webhook, header_record: dict
):
    """Bot-authored header is deleted via message.delete(), not webhook."""
    with (
        patch("db.headers.find_one", new_callable=AsyncMock, return_value=header_record),
        patch(_IS_APPROVED, return_value=True),
    ):
        await delete_header(ctx, bot_message)

    bot_message.delete.assert_awaited_once()
    webhook.delete_message.assert_not_awaited()


async def test_webhook_message_uses_webhook_delete(
    ctx: AsyncMock, webhook_message: discord.Message, webhook: discord.Webhook, header_record: dict
):
    """Webhook-authored header is deleted via webhook.delete_message()."""
    with (
        patch("db.headers.find_one", new_callable=AsyncMock, return_value=header_record),
        patch(_IS_APPROVED, return_value=True),
    ):
        await delete_header(ctx, webhook_message)

    webhook.delete_message.assert_awaited_once_with(webhook_message.id)
    webhook_message.delete.assert_not_awaited()


# --- Failure handling ---


async def test_forbidden_on_delete(
    ctx: AsyncMock, bot_message: discord.Message, header_record: dict
):
    """discord.Forbidden during deletion shows error message."""
    bot_message.delete = AsyncMock(side_effect=discord.errors.Forbidden(MagicMock(), "forbidden"))

    with (
        patch("db.headers.find_one", new_callable=AsyncMock, return_value=header_record),
        patch(_IS_APPROVED, return_value=True),
    ):
        await delete_header(ctx, bot_message)

    ctx.respond.assert_awaited_once()
    args, kwargs = ctx.respond.await_args
    assert "Something went wrong" in args[0]
    assert kwargs["ephemeral"] is True
