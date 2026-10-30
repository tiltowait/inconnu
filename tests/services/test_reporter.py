"""Tests for services/reporter.py's error handling."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import cast
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import discord
import pymongo.errors
import pytest
from discord.ext import commands

import errors
from bot import InconnuBot
from config import settings
from ctx import AppCtx, AppInteraction
from services.reporter import MAX_DESCRIPTION, ErrorReporter

UNKNOWN_MSG = "<@1> has encountered an error. Support has been notified!"


def make_ctx() -> AppCtx:
    """A context in a guild."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild = MagicMock(spec=discord.Guild)
    return ctx


def make_bot() -> InconnuBot:
    """A bot whose user is <@1>."""
    bot = MagicMock(spec=InconnuBot)
    bot.me = MagicMock(spec=discord.ClientUser)
    bot.me.mention = "<@1>"
    bot.invite_url = "https://discord.com/invite"
    bot.lockdown = None
    return bot


def make_error_ctx(bot: InconnuBot) -> AppCtx:
    """A command context in a guild, for error reports."""
    ctx = cast(MagicMock, make_ctx())
    ctx.bot = bot
    ctx.respond = AsyncMock()
    ctx.user = MagicMock(spec=discord.Member)
    ctx.user.configure_mock(name="tiltowait", id=42)
    ctx.guild.configure_mock(name="Test Guild", icon=None)
    command = MagicMock(spec=discord.SlashCommand)
    command.qualified_name = "vr"
    ctx.command = command
    ctx.channel = AsyncMock(spec=discord.TextChannel)
    return cast(AppCtx, ctx)


def make_interaction(bot: InconnuBot) -> AppInteraction:
    """A component interaction in a guild, for error reports."""
    inter = MagicMock(spec=AppInteraction)
    inter.client = bot
    inter.respond = AsyncMock()
    inter.user = MagicMock(spec=discord.Member)
    inter.user.configure_mock(name="tiltowait", id=42)
    inter.guild = MagicMock(spec=discord.Guild)
    inter.guild.configure_mock(name="Test Guild", icon=None)
    inter.channel = AsyncMock(spec=discord.TextChannel)
    return inter


def raised(error: Exception) -> Exception:
    """Raise and catch the error, so it has a traceback."""
    try:
        raise error
    except Exception as err:
        return err


@pytest.fixture
def bot() -> InconnuBot:
    """A mock bot."""
    return make_bot()


@pytest.fixture
def ctx(bot: InconnuBot) -> AppCtx:
    """A command context for error reports."""
    return make_error_ctx(bot)


@pytest.fixture
async def reporter(bot: InconnuBot) -> ErrorReporter:
    """A reporter with a report channel."""
    reporter = ErrorReporter()
    with patch.object(settings, "report_channel", None):
        await reporter.prepare_channel(bot)
    reporter.channel = AsyncMock(spec=discord.TextChannel)
    return reporter


@pytest.fixture
def mock_error() -> Iterator[AsyncMock]:
    """Patch ui.embeds.error."""
    with patch("ui.embeds.error", new_callable=AsyncMock) as mock:
        yield mock


def report_embed(reporter: ErrorReporter) -> discord.Embed:
    """The embed posted to the report channel."""
    send = cast(AsyncMock, cast(discord.TextChannel, reporter.channel).send)
    send.assert_awaited_once()
    assert send.await_args is not None
    return send.await_args.kwargs["embed"]


def assert_not_reported(reporter: ErrorReporter):
    """Nothing was posted to the report channel."""
    cast(AsyncMock, cast(discord.TextChannel, reporter.channel).send).assert_not_awaited()


# Known errors


@pytest.mark.parametrize(
    "error,message",
    [
        (commands.NoPrivateMessage(), "Sorry, this command can only be run in a server!"),
        (
            commands.MissingPermissions(["administrator"]),
            "Sorry, you don't have permission to do this!",
        ),
        (commands.NotOwner(), "Sorry, only <@1>'s owner may issue this command!"),
    ],
)
async def test_known_error_responds(
    reporter: ErrorReporter, ctx: AppCtx, error: Exception, message: str
):
    """Known errors get a canned, private response and aren't reported."""
    await reporter.report_error(ctx, error)

    cast(AsyncMock, ctx.respond).assert_awaited_once_with(message, ephemeral=True)
    assert_not_reported(reporter)


@pytest.mark.parametrize(
    "error",
    [
        discord.NotFound(MagicMock(status=404), "Unknown Message"),
        discord.DiscordServerError(MagicMock(status=503), "Service Unavailable"),
        errors.HandledError(),
    ],
)
async def test_ignored_error(reporter: ErrorReporter, ctx: AppCtx, error: discord.DiscordException):
    """Some errors are dropped silently."""
    await reporter.report_error(ctx, error)

    cast(AsyncMock, ctx.respond).assert_not_awaited()
    assert_not_reported(reporter)


@pytest.mark.parametrize(
    "error,title",
    [
        (errors.InvalidAttachment("Allowed file types: `.png`."), "Invalid file"),
        (errors.NotReady("Still loading."), "One moment, please"),
    ],
)
async def test_error_embed_with_reason(
    reporter: ErrorReporter,
    ctx: AppCtx,
    mock_error: AsyncMock,
    error: discord.DiscordException,
    title: str,
):
    """Some errors show their reason in an error embed."""
    await reporter.report_error(ctx, error)

    mock_error.assert_awaited_once_with(ctx, str(error), title=title)
    assert_not_reported(reporter)


async def test_not_premium(reporter: ErrorReporter, ctx: AppCtx, mock_error: AsyncMock):
    """Non-patrons are told which command needs premium."""
    cast(MagicMock, ctx.bot).cmd_mention.return_value = "</vr:1>"
    await reporter.report_error(ctx, errors.NotPremium())

    assert mock_error.await_args is not None
    assert "Only patrons can use </vr:1>." in mock_error.await_args.args[1]
    assert mock_error.await_args.kwargs["title"] == "Premium feature"
    assert_not_reported(reporter)


async def test_lockdown(reporter: ErrorReporter, ctx: AppCtx):
    """During lockdown, the user is told when maintenance happens."""
    cast(MagicMock, ctx.bot).lockdown = datetime(2026, 1, 1, tzinfo=UTC)
    await reporter.report_error(ctx, errors.LockdownError())

    respond = cast(AsyncMock, ctx.respond)
    assert respond.await_args is not None
    embed: discord.Embed = respond.await_args.kwargs["embed"]
    assert embed.title == "Command temporarily unavailable"
    assert respond.await_args.kwargs["ephemeral"] is True
    assert_not_reported(reporter)


async def test_lockdown_error_without_lockdown(reporter: ErrorReporter, ctx: AppCtx):
    """A LockdownError outside lockdown is reported as unknown."""
    await reporter.report_error(ctx, errors.LockdownError())

    cast(AsyncMock, ctx.respond).assert_awaited_once_with(UNKNOWN_MSG, ephemeral=True)
    assert report_embed(reporter).title == "VR: LockdownError"


async def test_partial_messageable(reporter: ErrorReporter, ctx: AppCtx):
    """Missing channel access asks the user to re-invite the bot."""
    error = AttributeError("'PartialMessageable' object has no attribute 'name'")
    await reporter.report_error(ctx, error)

    respond = cast(AsyncMock, ctx.respond)
    assert respond.await_args is not None
    assert respond.await_args.kwargs["embed"].title == "Please re-invite Inconnu"
    assert_not_reported(reporter)


async def test_original_error_unwrapped(reporter: ErrorReporter, ctx: AppCtx):
    """Errors wrapped by the command are handled as the original error."""
    wrapped = discord.ApplicationCommandInvokeError(commands.NoPrivateMessage())
    await reporter.report_error(ctx, wrapped)

    cast(AsyncMock, ctx.respond).assert_awaited_once_with(
        "Sorry, this command can only be run in a server!", ephemeral=True
    )


# Unknown errors


async def test_unknown_error(reporter: ErrorReporter, ctx: AppCtx):
    """Unknown errors notify the user, then post and log the traceback."""
    error = raised(ValueError("bad value"))
    with patch("services.reporter.logger") as mock_logger:
        await reporter.report_error(ctx, error)

    cast(AsyncMock, ctx.respond).assert_awaited_once_with(UNKNOWN_MSG, ephemeral=True)

    embed = report_embed(reporter)
    assert embed.title == "VR: ValueError"
    assert embed.description is not None
    assert embed.description.endswith("ValueError: bad value\n")
    assert "\n\n" not in embed.description
    assert embed.author is not None
    assert embed.author.name == "tiltowait (42) on Test Guild"

    mock_logger.error.assert_called_once_with("{}: {}", "VR", ANY)


async def test_unknown_error_in_dm(reporter: ErrorReporter, ctx: AppCtx):
    """The report's author line names DMs."""
    cast(MagicMock, ctx).guild = None
    await reporter.report_error(ctx, raised(ValueError()))

    author = report_embed(reporter).author
    assert author is not None
    assert author.name == "tiltowait (42) on DM"


async def test_long_traceback_truncated(reporter: ErrorReporter, ctx: AppCtx):
    """Long tracebacks keep their end, so the report still posts."""
    error = raised(ValueError("x" * 5000 + " the end"))
    with patch("services.reporter.logger") as mock_logger:
        await reporter.report_error(ctx, error)

    description = report_embed(reporter).description
    assert description is not None
    assert len(description) == MAX_DESCRIPTION
    assert description.startswith("…")
    assert description.endswith(" the end\n")

    # The log keeps the whole thing
    assert mock_logger.error.call_args is not None
    assert "Traceback" in mock_logger.error.call_args.args[2]


async def test_report_channel_failure_still_logs(reporter: ErrorReporter, ctx: AppCtx):
    """A failed report post doesn't raise, and the error is still logged."""
    send = cast(AsyncMock, cast(discord.TextChannel, reporter.channel).send)
    send.side_effect = discord.HTTPException(MagicMock(status=400), "Invalid Form Body")
    with patch("services.reporter.logger") as mock_logger:
        await reporter.report_error(ctx, raised(ValueError()))

    mock_logger.error.assert_any_call("{}: {}", "VR", ANY)


async def test_respond_failure_still_reports(reporter: ErrorReporter, ctx: AppCtx):
    """If the user can't be told, support still gets the report."""
    cast(AsyncMock, ctx.respond).side_effect = discord.NotFound(
        MagicMock(status=404), "Unknown interaction"
    )
    await reporter.report_error(ctx, raised(ValueError()))

    assert report_embed(reporter).title == "VR: ValueError"


async def test_unknown_error_without_report_channel(reporter: ErrorReporter, ctx: AppCtx):
    """Without a report channel, the user is still told."""
    reporter.channel = None
    await reporter.report_error(ctx, raised(ValueError()))

    cast(AsyncMock, ctx.respond).assert_awaited_once_with(UNKNOWN_MSG, ephemeral=True)


async def test_database_error(reporter: ErrorReporter, ctx: AppCtx, bot: InconnuBot):
    """Database errors get the outage notice and are reported."""
    error = raised(pymongo.errors.ServerSelectionTimeoutError("timed out"))
    with patch("services.reporter.report_database_error", new_callable=AsyncMock) as mock_db:
        await reporter.report_error(ctx, error)

    mock_db.assert_awaited_once_with(bot, ctx)
    assert report_embed(reporter).title == "VR: ServerSelectionTimeoutError"


async def test_database_error_report_failure_still_reports(reporter: ErrorReporter, ctx: AppCtx):
    """A failed database-error notice doesn't stop the error being logged and reported."""
    error = raised(pymongo.errors.ServerSelectionTimeoutError("timed out"))
    with (
        patch(
            "services.reporter.report_database_error",
            new_callable=AsyncMock,
            side_effect=AttributeError("'NoneType' object has no attribute 'send'"),
        ),
        patch("services.reporter.logger") as mock_logger,
    ):
        await reporter.report_error(ctx, error)

    mock_logger.error.assert_any_call("{}: {}", "VR", ANY)
    assert report_embed(reporter).title == "VR: ServerSelectionTimeoutError"


async def test_invalid_webhook_token(reporter: ErrorReporter, ctx: AppCtx):
    """Error 50027 alerts the channel to a Discord outage."""
    error = discord.HTTPException(
        MagicMock(status=401), {"code": 50027, "message": "Invalid Webhook Token"}
    )
    await reporter.report_error(ctx, raised(error))

    channel_send = cast(AsyncMock, cast(discord.TextChannel, ctx.channel).send)
    assert channel_send.await_args is not None
    assert "discordstatus.com" in channel_send.await_args.args[0]
    assert report_embed(reporter).description == (
        "**Unrecoverable Discord error:** Invalid webhook token"
    )


async def test_outage_alert_failure_still_reports(reporter: ErrorReporter, ctx: AppCtx):
    """A channel the bot can't post in doesn't stop the outage error being reported."""
    error = discord.HTTPException(
        MagicMock(status=401), {"code": 50027, "message": "Invalid Webhook Token"}
    )
    channel_send = cast(AsyncMock, cast(discord.TextChannel, ctx.channel).send)
    channel_send.side_effect = discord.Forbidden(MagicMock(status=403), "Missing Access")

    await reporter.report_error(ctx, raised(error))

    cast(AsyncMock, ctx.respond).assert_awaited_once_with(UNKNOWN_MSG, ephemeral=True)
    assert report_embed(reporter).description == (
        "**Unrecoverable Discord error:** Invalid webhook token"
    )


async def test_50027_in_message_is_not_outage(reporter: ErrorReporter, ctx: AppCtx):
    """Only the error code signals an outage, not the number in the message."""
    await reporter.report_error(ctx, raised(ValueError("Order 50027 not found")))

    cast(AsyncMock, cast(discord.TextChannel, ctx.channel).send).assert_not_awaited()
    assert report_embed(reporter).title == "VR: ValueError"


async def test_interaction_error(reporter: ErrorReporter, bot: InconnuBot):
    """Interaction errors are reported under INTERACTION."""
    inter = make_interaction(bot)
    await reporter.report_error(inter, raised(ValueError()))

    cast(AsyncMock, inter.respond).assert_awaited_once_with(UNKNOWN_MSG, ephemeral=True)
    assert report_embed(reporter).title == "INTERACTION: ValueError"


# Channel preparation


async def test_prepare_channel(bot: InconnuBot):
    """The configured text channel becomes the report channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = "errors"
    cast(MagicMock, bot).fetch_channel = AsyncMock(return_value=channel)
    reporter = ErrorReporter()
    with patch.object(settings, "report_channel", 123):
        await reporter.prepare_channel(bot)

    assert reporter.channel is channel
    assert reporter.bot is bot


async def test_prepare_channel_not_text(bot: InconnuBot):
    """Non-text channels are rejected."""
    cast(MagicMock, bot).fetch_channel = AsyncMock(
        return_value=MagicMock(spec=discord.VoiceChannel)
    )
    reporter = ErrorReporter()
    with patch.object(settings, "report_channel", 123):
        await reporter.prepare_channel(bot)

    assert reporter.channel is None


@pytest.mark.parametrize(
    "error",
    [
        discord.NotFound(MagicMock(status=404), "Unknown Channel"),
        discord.Forbidden(MagicMock(status=403), "Missing Access"),
    ],
)
async def test_prepare_channel_inaccessible(bot: InconnuBot, error: discord.HTTPException):
    """A deleted or inaccessible channel doesn't stop the bot from connecting."""
    cast(MagicMock, bot).fetch_channel = AsyncMock(side_effect=error)
    reporter = ErrorReporter()
    with patch.object(settings, "report_channel", 123):
        await reporter.prepare_channel(bot)

    assert reporter.channel is None
    assert reporter.bot is bot


def test_bot_before_prepare():
    """Using the bot before preparing the channel is a programming error."""
    with pytest.raises(RuntimeError):
        _ = ErrorReporter().bot
