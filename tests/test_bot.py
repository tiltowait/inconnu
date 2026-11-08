"""Tests for bot setup and event handlers."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
import pytest

import bot as bot_module
import errors
from bot import InconnuBot
from models import RPPost
from services import WebhookCache
from services.lockdown import LOCKDOWN_DELAY, Lockdown, LockdownReason
from services.webhooks import UNKNOWN_WEBHOOK

type MockChannel = MagicMock
type MockWebhook = AsyncMock

# Fixtures


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock InconnuBot instance."""
    bot = MagicMock(spec=InconnuBot)
    bot.guilds = []
    return bot


# Cog loading


async def test_missing_cog_dir_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A missing interface directory fails loudly instead of loading no cogs."""
    monkeypatch.setattr(bot_module, "__file__", str(tmp_path / "bot.py"))

    with pytest.raises(RuntimeError, match="No cogs found"):
        InconnuBot(intents=discord.Intents.none())


# Properties


def test_me_before_login(mock_bot: MagicMock):
    """The bot's user is unavailable before login."""
    mock_bot.user = None
    with pytest.raises(RuntimeError):
        InconnuBot.me.__get__(mock_bot)


def test_webhook_cache_before_connect(mock_bot: MagicMock):
    """The webhook cache is unavailable before connecting."""
    mock_bot._webhook_cache = None
    with pytest.raises(RuntimeError):
        InconnuBot.webhook_cache.__get__(mock_bot)


# Lockdown


def test_start_lockdown(mock_bot: MagicMock):
    """A lockdown records its reason and schedules the shutdown LOCKDOWN_DELAY out."""
    now = datetime(2026, 11, 1, 12, tzinfo=UTC)
    with patch.object(bot_module.discord.utils, "utcnow", return_value=now):
        lockdown = InconnuBot.start_lockdown(mock_bot, LockdownReason.UPDATE)

    assert lockdown == Lockdown(LockdownReason.UPDATE, now + LOCKDOWN_DELAY)
    assert mock_bot.lockdown is lockdown


def test_end_lockdown(mock_bot: MagicMock):
    """Ending a lockdown clears it."""
    InconnuBot.start_lockdown(mock_bot, LockdownReason.MAINTENANCE)
    InconnuBot.end_lockdown(mock_bot)
    assert mock_bot.lockdown is None


# Webhooks


def not_found(code: int) -> discord.NotFound:
    """A NotFound error with the given Discord error code."""
    response = MagicMock(spec=aiohttp.ClientResponse, status=404, reason="Not Found")
    return discord.NotFound(response, {"code": code, "message": "Unknown"})


def make_webhook(webhook_id: int) -> MockWebhook:
    """A webhook whose sends return a message."""
    webhook = AsyncMock(spec=discord.Webhook, id=webhook_id)
    webhook.send.return_value = MagicMock(spec=discord.WebhookMessage, id=webhook_id * 10)
    return webhook


@pytest.fixture
def text_channel() -> MockChannel:
    """A text channel."""
    return MagicMock(spec=discord.TextChannel)


@pytest.fixture
def webhook_bot(mock_bot: MagicMock) -> MagicMock:
    """A mock bot with a webhook cache and the real webhook methods."""
    mock_bot.webhook_cache = AsyncMock(spec=WebhookCache)
    mock_bot.prep_webhook = lambda channel: InconnuBot.prep_webhook(mock_bot, channel)
    return mock_bot


async def test_prep_webhook_outside_text_channel(webhook_bot: MagicMock):
    """Threads and other channels can't use webhooks."""
    channel = MagicMock(spec=discord.Thread)

    with pytest.raises(errors.WebhookError, match="text channels"):
        await InconnuBot.prep_webhook(webhook_bot, channel)

    webhook_bot.webhook_cache.prep_webhook.assert_not_awaited()


async def test_prep_webhook_without_permission(webhook_bot: MagicMock, text_channel: MockChannel):
    """Missing permissions become a WebhookError."""
    response = MagicMock(spec=aiohttp.ClientResponse, status=403, reason="Forbidden")
    webhook_bot.webhook_cache.prep_webhook.side_effect = discord.Forbidden(response, "Missing")

    with pytest.raises(errors.WebhookError, match="Manage Webhook"):
        await InconnuBot.prep_webhook(webhook_bot, text_channel)


async def test_webhook_send(webhook_bot: MagicMock, text_channel: MockChannel):
    """The message is sent through the channel's webhook, which is returned."""
    webhook = make_webhook(1)
    webhook_bot.webhook_cache.prep_webhook.return_value = webhook

    result = await InconnuBot.webhook_send(webhook_bot, text_channel, content="Hi")

    assert result == (webhook, webhook.send.return_value)
    webhook.send.assert_awaited_once_with(wait=True, content="Hi")
    webhook_bot.webhook_cache.forget.assert_not_called()


async def test_webhook_send_replaces_deleted_webhook(
    webhook_bot: MagicMock, text_channel: MockChannel
):
    """A webhook deleted behind the cache's back is replaced, and the message
    sent through the new one."""
    stale, fresh = make_webhook(1), make_webhook(2)
    stale.send.side_effect = not_found(UNKNOWN_WEBHOOK)
    webhook_bot.webhook_cache.prep_webhook.side_effect = [stale, fresh]

    result = await InconnuBot.webhook_send(webhook_bot, text_channel, content="Hi")

    assert result == (fresh, fresh.send.return_value)
    webhook_bot.webhook_cache.forget.assert_called_once_with(stale)
    fresh.send.assert_awaited_once_with(wait=True, content="Hi")


async def test_webhook_send_other_not_found(webhook_bot: MagicMock, text_channel: MockChannel):
    """Other NotFound errors don't replace the webhook."""
    webhook = make_webhook(1)
    webhook.send.side_effect = not_found(10003)  # Unknown Channel
    webhook_bot.webhook_cache.prep_webhook.return_value = webhook

    with pytest.raises(discord.NotFound):
        await InconnuBot.webhook_send(webhook_bot, text_channel, content="Hi")

    webhook_bot.webhook_cache.forget.assert_not_called()


# Rolepost reply pings

WEBHOOK_ID = 50
AUTHOR_ID = 200


def make_reply(
    *,
    bot_author: bool = False,
    reply: bool = True,
    reference: bool = True,
    resolved: bool = True,
    to_webhook: bool = True,
    mentions: list[int] | None = None,
) -> MagicMock:
    """A reply to a message, by default a resolved reply to one of our webhooks."""
    message = MagicMock(spec=discord.Message)
    message.author.bot = bot_author
    message.type = (
        discord.MessageType.reply if reply else discord.MessageType.thread_starter_message
    )
    message.mentions = [MagicMock(spec=discord.Member, id=m) for m in mentions or []]
    message.reply = AsyncMock()

    if not reference:
        message.reference = None
        return message

    message.reference = MagicMock(spec=discord.MessageReference)
    message.reference.message_id = 10
    if resolved:
        replied_to = MagicMock(spec=discord.Message)
        replied_to.author.id = WEBHOOK_ID if to_webhook else WEBHOOK_ID + 1
        message.reference.resolved = replied_to
    else:
        message.reference.resolved = None

    return message


@pytest.fixture
def reply_bot(mock_bot: MagicMock) -> MagicMock:
    """A mock bot that knows our webhook and can fetch the Rolepost's author."""
    mock_bot.webhook_cache = MagicMock(spec=WebhookCache)
    mock_bot.webhook_cache.webhook_ids = {WEBHOOK_ID}
    author = MagicMock(spec=discord.User)
    author.configure_mock(id=AUTHOR_ID, mention=f"<@{AUTHOR_ID}>", name="Author")
    mock_bot.get_or_fetch_user = AsyncMock(return_value=author)
    return mock_bot


@pytest.fixture
async def mock_find_post() -> AsyncGenerator[AsyncMock]:
    """RPPost.find_one(), patched to return a Rolepost by AUTHOR_ID."""
    rp_post = MagicMock(spec=RPPost)
    rp_post.user = AUTHOR_ID
    with patch.object(RPPost, "find_one", new_callable=AsyncMock, return_value=rp_post) as mock:
        yield mock


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bot_author": True},
        {"reply": False},
        {"reference": False},
        {"resolved": False},
        {"to_webhook": False},
    ],
)
async def test_on_message_ignored(reply_bot: MagicMock, mock_find_post: AsyncMock, kwargs: dict):
    """Messages that aren't user replies to our webhooks are ignored."""
    message = make_reply(**kwargs)
    await InconnuBot.on_message(reply_bot, message)

    mock_find_post.assert_not_awaited()
    message.reply.assert_not_awaited()


async def test_on_message_no_rolepost(reply_bot: MagicMock, mock_find_post: AsyncMock):
    """Replies to webhook messages that aren't Roleposts are ignored."""
    mock_find_post.return_value = None
    message = make_reply()
    await InconnuBot.on_message(reply_bot, message)

    mock_find_post.assert_awaited_once_with({"id_chain": 10})
    message.reply.assert_not_awaited()


async def test_on_message_author_already_mentioned(reply_bot: MagicMock, mock_find_post: AsyncMock):
    """No ping when the replier already pinged the Rolepost's author."""
    message = make_reply(mentions=[AUTHOR_ID])
    await InconnuBot.on_message(reply_bot, message)

    message.reply.assert_not_awaited()


async def test_on_message_pings_author(reply_bot: MagicMock, mock_find_post: AsyncMock):
    """Replies to a Rolepost ping its author."""
    message = make_reply(mentions=[AUTHOR_ID + 1])
    await InconnuBot.on_message(reply_bot, message)

    reply_bot.get_or_fetch_user.assert_awaited_once_with(AUTHOR_ID)
    message.reply.assert_awaited_once_with(f"<@{AUTHOR_ID}>", mention_author=False, delete_after=60)
