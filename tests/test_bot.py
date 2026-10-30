"""Tests for bot setup and event handlers."""

from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import bot as bot_module
import errors
import services
from bot import InconnuBot
from ctx import AppCtx
from models import RPPost, VChar
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


# Post-command tips and MOTD


def make_ctx(command: str = "vr", options: dict[str, str] | None = None) -> MagicMock:
    """A guild command context with the given options."""
    ctx = MagicMock(spec=AppCtx)
    ctx.command = MagicMock(spec=discord.SlashCommand)
    ctx.command.qualified_name = command
    ctx.interaction = MagicMock(spec=discord.Interaction)
    ctx.interaction.data = {
        "options": [{"name": k, "value": v} for k, v in (options or {}).items()]
    }
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.user = MagicMock(spec=discord.Member)
    ctx.user.configure_mock(id=1, name="User")
    return ctx


def make_char(*, is_pc: bool = True) -> MagicMock:
    """A character, PC or SPC."""
    char = MagicMock(spec=VChar)
    char.is_pc = is_pc
    return char


@pytest.fixture
async def mock_cmd_replace() -> AsyncGenerator[AsyncMock, None]:
    """cmd_replace(), patched, with the pre-send sleep skipped."""
    with (
        patch("bot.cmd_replace", new_callable=AsyncMock) as mock,
        patch("bot.asyncio.sleep", new_callable=AsyncMock),
    ):
        yield mock


@pytest.fixture
async def mock_char_mgr() -> AsyncGenerator[MagicMock, None]:
    """char_mgr's character_count() and fetchone(), patched for one PC."""
    with (
        patch.object(services.char_mgr, "character_count", new_callable=AsyncMock) as count,
        patch.object(services.char_mgr, "fetchone", new_callable=AsyncMock) as fetchone,
    ):
        count.return_value = 1
        fetchone.return_value = make_char()
        yield MagicMock(character_count=count, fetchone=fetchone)


async def test_tip_shown_for_single_pc(
    mock_bot: MagicMock, mock_cmd_replace: AsyncMock, mock_char_mgr: MagicMock
):
    """Users with one character are told they don't need the character option."""
    ctx = make_ctx(options={"character": "Nadea"})
    await InconnuBot._tip_unneeded_character_option(mock_bot, ctx)

    mock_char_mgr.fetchone.assert_awaited_once_with(ctx.guild, ctx.user, "Nadea")
    mock_cmd_replace.assert_awaited_once()
    assert mock_cmd_replace.await_args is not None
    assert "`/vr`" in mock_cmd_replace.await_args.args[1]


@pytest.mark.parametrize(
    "command,options",
    [
        ("vr", {}),
        ("vr", {"character": "Nadea", "player": "2"}),
        ("transfer", {"character": "Nadea"}),
    ],
)
async def test_tip_not_applicable(
    mock_bot: MagicMock,
    mock_cmd_replace: AsyncMock,
    mock_char_mgr: MagicMock,
    command: str,
    options: dict[str, str],
):
    """No tip without the character option, with a player, or when the option is required."""
    await InconnuBot._tip_unneeded_character_option(mock_bot, make_ctx(command, options))

    mock_char_mgr.character_count.assert_not_awaited()
    mock_cmd_replace.assert_not_awaited()


async def test_tip_not_shown_in_dms(
    mock_bot: MagicMock, mock_cmd_replace: AsyncMock, mock_char_mgr: MagicMock
):
    """No tip outside of guilds."""
    ctx = make_ctx(options={"character": "Nadea"})
    ctx.guild = None
    await InconnuBot._tip_unneeded_character_option(mock_bot, ctx)

    mock_cmd_replace.assert_not_awaited()


async def test_tip_not_shown_for_multiple_characters(
    mock_bot: MagicMock, mock_cmd_replace: AsyncMock, mock_char_mgr: MagicMock
):
    """Users with several characters need the option."""
    mock_char_mgr.character_count.return_value = 2
    await InconnuBot._tip_unneeded_character_option(
        mock_bot, make_ctx(options={"character": "Nadea"})
    )

    mock_char_mgr.fetchone.assert_not_awaited()
    mock_cmd_replace.assert_not_awaited()


async def test_tip_not_shown_for_spc(
    mock_bot: MagicMock, mock_cmd_replace: AsyncMock, mock_char_mgr: MagicMock
):
    """Users rolling an SPC need the option, even with one character of their own."""
    mock_char_mgr.fetchone.return_value = make_char(is_pc=False)
    await InconnuBot._tip_unneeded_character_option(
        mock_bot, make_ctx(options={"character": "Nadea"})
    )

    mock_cmd_replace.assert_not_awaited()


async def test_tip_not_shown_for_missing_character(
    mock_bot: MagicMock, mock_cmd_replace: AsyncMock, mock_char_mgr: MagicMock
):
    """No tip when the named character doesn't exist."""
    mock_char_mgr.fetchone.side_effect = errors.CharacterNotFoundError("Not found")
    await InconnuBot._tip_unneeded_character_option(
        mock_bot, make_ctx(options={"character": "Nadea"})
    )

    mock_cmd_replace.assert_not_awaited()


@pytest.fixture
def motd_bot(mock_bot: MagicMock) -> MagicMock:
    """A mock bot with an MOTD that nobody has seen."""
    mock_bot.motd = discord.Embed(title="News")
    mock_bot.motd_given = set()
    return mock_bot


async def test_motd_shown_once(motd_bot: MagicMock, mock_cmd_replace: AsyncMock):
    """Each user sees the MOTD only once."""
    ctx = make_ctx()
    await InconnuBot._show_motd(motd_bot, ctx)
    await InconnuBot._show_motd(motd_bot, ctx)

    mock_cmd_replace.assert_awaited_once_with(ctx, embed=motd_bot.motd, ephemeral=True)
    assert motd_bot.motd_given == {ctx.user.id}


async def test_motd_not_shown_for_exempt_command(motd_bot: MagicMock, mock_cmd_replace: AsyncMock):
    """The MOTD commands don't show the MOTD."""
    await InconnuBot._show_motd(motd_bot, make_ctx("motd"))

    mock_cmd_replace.assert_not_awaited()


async def test_motd_not_set(motd_bot: MagicMock, mock_cmd_replace: AsyncMock):
    """Nothing is shown without an MOTD."""
    motd_bot.motd = None
    await InconnuBot._show_motd(motd_bot, make_ctx())

    mock_cmd_replace.assert_not_awaited()


async def test_motd_failure_not_recorded(motd_bot: MagicMock, mock_cmd_replace: AsyncMock):
    """A user whose MOTD couldn't be sent will get it next time."""
    mock_cmd_replace.side_effect = discord.HTTPException(MagicMock(status=500), "Failed")
    await InconnuBot._show_motd(motd_bot, make_ctx())

    assert motd_bot.motd_given == set()
