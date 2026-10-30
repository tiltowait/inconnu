"""Tests for bot setup and event handlers."""

from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import bot as bot_module
from bot import InconnuBot
from models import RPPost
from services import WebhookCache

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


# Rolepost reply pings

WEBHOOK_ID = 50
AUTHOR_ID = 200


def make_reply(
    *,
    bot_author: bool = False,
    reference: bool = True,
    resolved: bool = True,
    to_webhook: bool = True,
    mentions: list[int] | None = None,
) -> MagicMock:
    """A reply to a message, by default a resolved reply to one of our webhooks."""
    message = MagicMock(spec=discord.Message)
    message.author.bot = bot_author
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
async def mock_find_post() -> AsyncGenerator[AsyncMock, None]:
    """RPPost.find_one(), patched to return a Rolepost by AUTHOR_ID."""
    rp_post = MagicMock(spec=RPPost)
    rp_post.user = AUTHOR_ID
    with patch.object(RPPost, "find_one", new_callable=AsyncMock, return_value=rp_post) as mock:
        yield mock


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bot_author": True},
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
