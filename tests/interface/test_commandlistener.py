"""Tests for interface/commandlistener.py's post-command steps."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import errors
import interface.commandlistener as listener_module
import services
from bot import InconnuBot
from ctx import AppCtx
from interface.commandlistener import CommandListener
from models import VChar

type MockCtx = MagicMock
type MockChar = MagicMock

CREATED_AT = datetime(2026, 10, 31, tzinfo=UTC)


def make_ctx(command: str = "vr", options: dict[str, str] | None = None) -> MockCtx:
    """A guild command context with the given options."""
    ctx = MagicMock(spec=AppCtx)
    ctx.command = MagicMock(spec=discord.SlashCommand)
    ctx.command.qualified_name = command
    ctx.command.type = 1
    ctx.interaction = MagicMock(spec=discord.Interaction)
    ctx.interaction.data = {
        "options": [{"name": k, "value": v} for k, v in (options or {}).items()]
    }
    ctx.interaction.locale = "en-US"
    ctx.interaction.created_at = CREATED_AT
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.name = "Chronicle"
    ctx.guild_id = 10
    ctx.user = MagicMock(spec=discord.Member)
    ctx.user.configure_mock(id=1, name="User")
    return ctx


def make_char(*, is_pc: bool = True) -> MockChar:
    """A character, PC or SPC."""
    char = MagicMock(spec=VChar)
    char.is_pc = is_pc
    return char


@pytest.fixture
def cog() -> CommandListener:
    """A CommandListener on a mock bot with an MOTD that nobody has seen."""
    bot = MagicMock(spec=InconnuBot)
    bot.motd = discord.Embed(title="News")
    bot.motd_given = set()
    return CommandListener(bot)


# The cog module is patched directly: loading a real InconnuBot elsewhere in the
# suite replaces sys.modules["interface.commandlistener"] with a fresh copy.


@pytest.fixture
async def mock_cmd_replace_respond() -> AsyncGenerator[AsyncMock]:
    """cmd_replace_respond(), patched, with the pre-send sleep skipped."""
    with (
        patch.object(listener_module, "cmd_replace_respond", new_callable=AsyncMock) as mock,
        patch.object(listener_module.asyncio, "sleep", new_callable=AsyncMock),
    ):
        yield mock


@pytest.fixture
async def mock_command_log() -> AsyncGenerator[AsyncMock]:
    """The command log's insert_one(), patched."""
    with patch.object(listener_module.db.command_log, "insert_one", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
async def mock_char_mgr() -> AsyncGenerator[MagicMock]:
    """char_mgr's character_count() and fetchone(), patched for one PC."""
    with (
        patch.object(services.char_mgr, "character_count", new_callable=AsyncMock) as count,
        patch.object(services.char_mgr, "fetchone", new_callable=AsyncMock) as fetchone,
    ):
        count.return_value = 1
        fetchone.return_value = make_char()
        yield MagicMock(character_count=count, fetchone=fetchone)


# Steps


async def test_steps_run_in_order(cog: CommandListener):
    """Logging comes first, then the tip, then the MOTD."""
    calls = []
    steps = ("_log_command", "_tip_unneeded_character_option", "_show_motd")
    with (
        patch.object(cog, steps[0], AsyncMock(side_effect=lambda *_: calls.append(steps[0]))),
        patch.object(cog, steps[1], AsyncMock(side_effect=lambda *_: calls.append(steps[1]))),
        patch.object(cog, steps[2], AsyncMock(side_effect=lambda *_: calls.append(steps[2]))),
    ):
        await cog.on_application_command(make_ctx())

    assert calls == list(steps)


async def test_failed_step_doesnt_stop_the_rest(
    cog: CommandListener, mock_command_log: AsyncMock, mock_cmd_replace_respond: AsyncMock
):
    """If logging fails, the MOTD is still shown."""
    mock_command_log.side_effect = RuntimeError("Database down")
    ctx = make_ctx()
    await cog.on_application_command(ctx)

    mock_cmd_replace_respond.assert_awaited_once_with(ctx, embed=cog.bot.motd, ephemeral=True)


async def test_no_command(cog: CommandListener, mock_command_log: AsyncMock):
    """Nothing runs without a command."""
    ctx = make_ctx()
    ctx.command = None
    await cog.on_application_command(ctx)

    mock_command_log.assert_not_awaited()


# Logging


async def test_command_logged(cog: CommandListener, mock_command_log: AsyncMock):
    """Commands are recorded in the command log."""
    await cog._log_command(make_ctx(options={"character": "Nadea"}), "vr")

    mock_command_log.assert_awaited_once_with(
        {
            "guild": 10,
            "user": 1,
            "locale": "en-US",
            "command": "vr",
            "type": 1,
            "options": [{"name": "character", "value": "Nadea"}],
            "date": CREATED_AT,
        }
    )


# Tips


async def test_tip_shown_for_single_pc(
    cog: CommandListener, mock_cmd_replace_respond: AsyncMock, mock_char_mgr: MagicMock
):
    """Users with one character are told they don't need the character option."""
    ctx = make_ctx(options={"character": "Nadea"})
    await cog._tip_unneeded_character_option(ctx, "vr")

    mock_char_mgr.fetchone.assert_awaited_once_with(ctx.guild, ctx.user, "Nadea")
    mock_cmd_replace_respond.assert_awaited_once()
    assert mock_cmd_replace_respond.await_args is not None
    assert "`/vr`" in mock_cmd_replace_respond.await_args.args[1]


@pytest.mark.parametrize(
    "command,options",
    [
        ("vr", {}),
        ("vr", {"character": "Nadea", "player": "2"}),
        ("transfer", {"character": "Nadea"}),
    ],
)
async def test_tip_not_applicable(
    cog: CommandListener,
    mock_cmd_replace_respond: AsyncMock,
    mock_char_mgr: MagicMock,
    command: str,
    options: dict[str, str],
):
    """No tip without the character option, with a player, or when the option is required."""
    await cog._tip_unneeded_character_option(make_ctx(command, options), command)

    mock_char_mgr.character_count.assert_not_awaited()
    mock_cmd_replace_respond.assert_not_awaited()


async def test_tip_not_shown_in_dms(
    cog: CommandListener, mock_cmd_replace_respond: AsyncMock, mock_char_mgr: MagicMock
):
    """No tip outside of guilds."""
    ctx = make_ctx(options={"character": "Nadea"})
    ctx.guild = None
    await cog._tip_unneeded_character_option(ctx, "vr")

    mock_cmd_replace_respond.assert_not_awaited()


async def test_tip_not_shown_for_multiple_characters(
    cog: CommandListener, mock_cmd_replace_respond: AsyncMock, mock_char_mgr: MagicMock
):
    """Users with several characters need the option."""
    mock_char_mgr.character_count.return_value = 2
    await cog._tip_unneeded_character_option(make_ctx(options={"character": "Nadea"}), "vr")

    mock_char_mgr.fetchone.assert_not_awaited()
    mock_cmd_replace_respond.assert_not_awaited()


async def test_tip_not_shown_for_spc(
    cog: CommandListener, mock_cmd_replace_respond: AsyncMock, mock_char_mgr: MagicMock
):
    """Users rolling an SPC need the option, even with one character of their own."""
    mock_char_mgr.fetchone.return_value = make_char(is_pc=False)
    await cog._tip_unneeded_character_option(make_ctx(options={"character": "Nadea"}), "vr")

    mock_cmd_replace_respond.assert_not_awaited()


async def test_tip_not_shown_for_missing_character(
    cog: CommandListener, mock_cmd_replace_respond: AsyncMock, mock_char_mgr: MagicMock
):
    """No tip when the named character doesn't exist."""
    mock_char_mgr.fetchone.side_effect = errors.CharacterNotFoundError("Not found")
    await cog._tip_unneeded_character_option(make_ctx(options={"character": "Nadea"}), "vr")

    mock_cmd_replace_respond.assert_not_awaited()


# MOTD


async def test_motd_shown_once(cog: CommandListener, mock_cmd_replace_respond: AsyncMock):
    """Each user sees the MOTD only once."""
    ctx = make_ctx()
    await cog._show_motd(ctx, "vr")
    await cog._show_motd(ctx, "vr")

    mock_cmd_replace_respond.assert_awaited_once_with(ctx, embed=cog.bot.motd, ephemeral=True)
    assert cog.bot.motd_given == {ctx.user.id}


@pytest.mark.parametrize("command", ["motd", "announce"])
async def test_motd_not_shown_for_exempt_command(
    cog: CommandListener, mock_cmd_replace_respond: AsyncMock, command: str
):
    """The MOTD commands don't show the MOTD."""
    await cog._show_motd(make_ctx(command), command)

    mock_cmd_replace_respond.assert_not_awaited()


async def test_motd_not_set(cog: CommandListener, mock_cmd_replace_respond: AsyncMock):
    """Nothing is shown without an MOTD."""
    cog.bot.motd = None
    await cog._show_motd(make_ctx(), "vr")

    mock_cmd_replace_respond.assert_not_awaited()


async def test_motd_failure_not_recorded(cog: CommandListener, mock_cmd_replace_respond: AsyncMock):
    """A user whose MOTD couldn't be sent will get it next time."""
    mock_cmd_replace_respond.side_effect = discord.HTTPException(MagicMock(status=500), "Failed")
    await cog._show_motd(make_ctx(), "vr")

    assert cog.bot.motd_given == set()
