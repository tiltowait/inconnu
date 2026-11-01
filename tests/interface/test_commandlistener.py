"""Tests for interface/commandlistener.py's post-command steps."""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
import pytest
from mongomock_motor import AsyncMongoMockClient

import errors
import interface.commandlistener as listener_module
import services
from bot import InconnuBot
from ctx import AppCtx
from inconnu.misc.changelog import ReleaseInfo
from interface.commandlistener import CommandListener
from models import VChar, VUser
from ui.views import PagedView

type MockCtx = MagicMock
type MockChar = MagicMock

CREATED_AT = datetime(2026, 10, 31, tzinfo=UTC)
RELEASE = ReleaseInfo(tag="v2026.10.31", text="## Fixes\n- A fix", published_at=CREATED_AT)


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
    """Logging comes first, then a wait for the command's response, then the follow-ups."""
    calls = []
    steps = ("_log_command", "_tip_unneeded_character_option", "_show_motd", "_show_changelog")

    def record(name: str) -> AsyncMock:
        """A mock that records its call."""
        return AsyncMock(side_effect=lambda *_: calls.append(name))

    with (
        patch.object(listener_module.asyncio, "sleep", record("sleep")),
        patch.object(cog, steps[0], record(steps[0])),
        patch.object(cog, steps[1], record(steps[1])),
        patch.object(cog, steps[2], record(steps[2])),
        patch.object(cog, steps[3], record(steps[3])),
    ):
        await cog.on_application_command(make_ctx())

    assert calls == [steps[0], "sleep", *steps[1:]]


async def test_failed_step_doesnt_stop_the_rest(
    cog: CommandListener, mock_command_log: AsyncMock, mock_cmd_replace_respond: AsyncMock
):
    """If logging fails, the MOTD is still shown."""
    mock_command_log.side_effect = RuntimeError("Database down")
    ctx = make_ctx()
    with patch.object(cog, "_show_changelog", AsyncMock()):
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


# Changelog


@pytest.fixture
async def command_log() -> AsyncGenerator[Any]:
    """An empty command log."""
    collection = AsyncMongoMockClient().test.command_log
    with patch.object(listener_module.db, "command_log", collection):
        yield collection


@pytest.fixture
async def mock_fetch_changelog() -> AsyncGenerator[AsyncMock]:
    """fetch_changelog(), patched to return RELEASE."""
    with patch.object(
        listener_module.changelog, "fetch_changelog", AsyncMock(return_value=RELEASE)
    ) as mock:
        yield mock


@pytest.fixture
async def changelog_ctx(command_log: Any) -> AsyncGenerator[MockCtx]:
    """A returning user's command, with no VUser saved or cached."""
    ctx = make_ctx()
    # A property on ApplicationContext, so the spec can't infer it
    ctx.respond = AsyncMock()
    await command_log.insert_one({"user": ctx.user.id, "date": CREATED_AT - timedelta(days=1)})

    VUser.get_or_fetch.cache_clear()
    await VUser.find({"user": ctx.user.id}).delete()
    yield ctx
    VUser.get_or_fetch.cache_clear()
    await VUser.find({"user": ctx.user.id}).delete()


async def saved_version(ctx: MockCtx) -> str | None:
    """The user's saved last_version_used, if they have a VUser."""
    vuser = await VUser.find_one({"user": ctx.user.id})
    return vuser.last_version_used if vuser is not None else None


def changelog_shown(ctx: MockCtx) -> bool:
    """Whether the changelog was sent to the user."""
    if not ctx.respond.await_count:
        return False
    ctx.respond.assert_awaited_once()
    kwargs = ctx.respond.await_args.kwargs
    assert kwargs["ephemeral"]
    assert isinstance(kwargs["view"], PagedView)
    return True


async def test_changelog_shown_to_returning_user(
    cog: CommandListener, changelog_ctx: MockCtx, mock_fetch_changelog: AsyncMock
):
    """A returning user without a VUser sees the changelog, and their version is saved."""
    await cog._show_changelog(changelog_ctx, "vr")

    assert changelog_shown(changelog_ctx)
    assert await saved_version(changelog_ctx) == RELEASE.tag


async def test_changelog_shown_after_update(
    cog: CommandListener, changelog_ctx: MockCtx, mock_fetch_changelog: AsyncMock
):
    """A user who saw an older release sees the new one, and their settings are kept."""
    vuser = VUser(user=changelog_ctx.user.id, last_version_used="v2026.01.01")
    vuser.settings.accessibility = True
    await vuser.save()

    await cog._show_changelog(changelog_ctx, "vr")

    assert changelog_shown(changelog_ctx)
    saved = await VUser.find_one({"user": changelog_ctx.user.id})
    assert saved is not None
    assert saved.last_version_used == RELEASE.tag
    assert saved.settings.accessibility


async def test_changelog_shown_once(
    cog: CommandListener, changelog_ctx: MockCtx, mock_fetch_changelog: AsyncMock
):
    """A user sees each release's changelog only once, even after leaving the cache."""
    await cog._show_changelog(changelog_ctx, "vr")
    VUser.get_or_fetch.cache_clear()
    await cog._show_changelog(changelog_ctx, "vr")

    changelog_ctx.respond.assert_awaited_once()


@pytest.mark.parametrize(
    "user_id,offset",
    [
        (1, timedelta(0)),  # The triggering command, already logged
        (2, -timedelta(days=1)),  # Someone else's command
    ],
)
async def test_changelog_not_shown_to_new_user(
    cog: CommandListener,
    changelog_ctx: MockCtx,
    command_log: Any,
    mock_fetch_changelog: AsyncMock,
    user_id: int,
    offset: timedelta,
):
    """A user whose first command this is doesn't see it, but their version is saved."""
    await command_log.delete_many({})
    await command_log.insert_one({"user": user_id, "date": CREATED_AT + offset})

    await cog._show_changelog(changelog_ctx, "vr")

    assert not changelog_shown(changelog_ctx)
    assert await saved_version(changelog_ctx) == RELEASE.tag


async def test_changelog_not_shown_after_changelog_command(
    cog: CommandListener, changelog_ctx: MockCtx, mock_fetch_changelog: AsyncMock
):
    """Running /changelog doesn't show it twice, but counts as seeing it."""
    await cog._show_changelog(changelog_ctx, "changelog")

    assert not changelog_shown(changelog_ctx)
    assert await saved_version(changelog_ctx) == RELEASE.tag


async def test_changelog_fetch_failure(
    cog: CommandListener, changelog_ctx: MockCtx, mock_fetch_changelog: AsyncMock
):
    """Nothing is shown or saved if the changelog can't be fetched."""
    mock_fetch_changelog.side_effect = aiohttp.ClientError()
    await cog._show_changelog(changelog_ctx, "vr")

    assert not changelog_shown(changelog_ctx)
    assert await saved_version(changelog_ctx) is None


async def test_changelog_retried_after_fetch_failure(
    cog: CommandListener, changelog_ctx: MockCtx, mock_fetch_changelog: AsyncMock
):
    """A failed fetch doesn't stop the user seeing the changelog later."""
    mock_fetch_changelog.side_effect = [aiohttp.ClientError(), RELEASE]
    await cog._show_changelog(changelog_ctx, "vr")
    await cog._show_changelog(changelog_ctx, "vr")

    assert changelog_shown(changelog_ctx)


async def test_changelog_retried_after_error(
    cog: CommandListener, changelog_ctx: MockCtx, mock_fetch_changelog: AsyncMock
):
    """An unexpected error doesn't stop the user seeing the changelog later."""
    changelog_ctx.respond.side_effect = [
        discord.HTTPException(MagicMock(status=500), "Failed"),
        None,
    ]
    with pytest.raises(discord.HTTPException):
        await cog._show_changelog(changelog_ctx, "vr")
    await cog._show_changelog(changelog_ctx, "vr")

    assert changelog_ctx.respond.await_count == 2


async def test_changelog_retried_after_vuser_lookup_error(
    cog: CommandListener, changelog_ctx: MockCtx, mock_fetch_changelog: AsyncMock
):
    """A failed VUser lookup doesn't stop the user seeing the changelog later."""
    with (
        patch.object(VUser, "get_or_fetch", AsyncMock(side_effect=RuntimeError("DB down"))),
        pytest.raises(RuntimeError),
    ):
        await cog._show_changelog(changelog_ctx, "vr")
    await cog._show_changelog(changelog_ctx, "vr")

    assert changelog_shown(changelog_ctx)


def blocking_fetch(release: asyncio.Event) -> Callable[[], Awaitable[ReleaseInfo]]:
    """A fetch_changelog() that waits for the event."""

    async def fetch() -> ReleaseInfo:
        await release.wait()
        return RELEASE

    return fetch


async def test_changelog_shown_once_for_simultaneous_commands(
    cog: CommandListener, changelog_ctx: MockCtx, mock_fetch_changelog: AsyncMock
):
    """A second command while the first is showing it doesn't show it again."""
    responding = asyncio.Event()
    release = asyncio.Event()

    async def respond(**_: Any):
        """Hold the first command mid-response, before it saves the version."""
        responding.set()
        await release.wait()

    changelog_ctx.respond.side_effect = respond
    first = asyncio.create_task(cog._show_changelog(changelog_ctx, "vr"))
    await responding.wait()

    # Without the guard, the second would also block in respond()
    second = asyncio.create_task(cog._show_changelog(changelog_ctx, "vr"))
    await asyncio.wait({second}, timeout=1)
    release.set()
    await asyncio.gather(first, second)

    changelog_ctx.respond.assert_awaited_once()


async def test_simultaneous_commands_from_other_users(
    cog: CommandListener,
    changelog_ctx: MockCtx,
    command_log: Any,
    mock_fetch_changelog: AsyncMock,
):
    """One user's pending changelog doesn't hold up another's."""
    other = make_ctx()
    other.user.id = 2
    # A property on ApplicationContext, so the spec can't infer it
    other.respond = AsyncMock()
    await command_log.insert_one({"user": 2, "date": CREATED_AT - timedelta(days=1)})
    await VUser.find({"user": 2}).delete()

    release = asyncio.Event()
    mock_fetch_changelog.side_effect = blocking_fetch(release)

    first = asyncio.create_task(cog._show_changelog(changelog_ctx, "vr"))
    await asyncio.sleep(0)  # Let the first reach the fetch
    second = asyncio.create_task(cog._show_changelog(other, "vr"))
    await asyncio.sleep(0)
    release.set()
    await asyncio.gather(first, second)

    assert changelog_shown(changelog_ctx)
    assert changelog_shown(other)
    await VUser.find({"user": 2}).delete()
