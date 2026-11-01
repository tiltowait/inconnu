"""Tests for interface/admin.py's lockdown commands."""

from collections.abc import Callable, Generator
from contextlib import AbstractContextManager
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest

import interface.admin as admin_module
from bot import InconnuBot
from ctx import AppCtx
from services.lockdown import LockdownReason
from services.wizard import WizardCache

type MockBot = MagicMock
type MockCtx = MagicMock

RESTART = "Inconnu can restart now."


@pytest.fixture
def bot() -> MockBot:
    """A bot whose lockdown methods are the real ones."""
    bot = MagicMock(spec=InconnuBot)
    bot.lockdown = None
    bot.me = MagicMock(spec=discord.ClientUser)
    bot.me.display_name = "Inconnu"
    bot.cmd_mention.return_value = "</wizards:1>"
    bot.start_lockdown.side_effect = lambda reason: InconnuBot.start_lockdown(bot, reason)
    bot.end_lockdown.side_effect = lambda: InconnuBot.end_lockdown(bot)
    return bot


@pytest.fixture
def cog(bot: MockBot) -> admin_module.AdminCog:
    """The admin cog on the mock bot."""
    return admin_module.AdminCog(bot)


@pytest.fixture
def ctx() -> MockCtx:
    """A command context, invoked just now, that records responses and edits."""
    ctx = MagicMock(spec=AppCtx)
    ctx.interaction = MagicMock(spec=discord.Interaction)
    ctx.interaction.created_at = discord.utils.utcnow()
    ctx.respond = AsyncMock()
    ctx.edit = AsyncMock()
    return ctx


@pytest.fixture
def mock_sleep() -> Generator[AsyncMock]:
    """asyncio.sleep(), patched so the wizard loop doesn't wait."""
    with patch.object(admin_module.asyncio, "sleep", new_callable=AsyncMock) as mock:
        yield mock


def running_wizards(*counts: int) -> AbstractContextManager[MagicMock]:
    """Patch the wizard cache to report each count in turn."""
    cache = MagicMock(spec=WizardCache)
    type(cache).count = PropertyMock(side_effect=counts)
    return patch.object(admin_module.services, "wizard_cache", cache)


def header(bot: MockBot) -> str:
    """The lockdown confirmation that heads every edit."""
    return f"Lockdown set for {discord.utils.format_dt(bot.lockdown.shutdown_time, 't')}."


def edits(ctx: MockCtx) -> list[str]:
    """The content of each edit to the response."""
    return [call.kwargs["content"] for call in ctx.edit.await_args_list]


async def start(cog: admin_module.AdminCog, ctx: MockCtx, reason: str = "update"):
    """Invoke /lockdown start."""
    await cog.lockdown_start.callback(cog, ctx, reason)


async def test_lockdown_start_without_wizards(
    cog: admin_module.AdminCog, bot: MockBot, ctx: MockCtx, mock_sleep: AsyncMock
):
    """With no wizards running, the bot can restart immediately."""
    with running_wizards(0):
        await start(cog, ctx, "maintenance")

    assert bot.lockdown.reason == LockdownReason.MAINTENANCE
    ctx.respond.assert_awaited_once_with(header(bot), ephemeral=True)
    assert edits(ctx) == [f"{header(bot)}\n{RESTART}"]
    mock_sleep.assert_not_awaited()


async def test_lockdown_start_waits_for_wizards(
    cog: admin_module.AdminCog, bot: MockBot, ctx: MockCtx, mock_sleep: AsyncMock
):
    """The wizard count updates until none are left."""
    with running_wizards(2, 1, 0):
        await start(cog, ctx)

    assert edits(ctx) == [
        f"{header(bot)}\n**Wizards running:** 2",
        f"{header(bot)}\n**Wizards running:** 1",
        f"{header(bot)}\n{RESTART}",
    ]
    assert mock_sleep.await_count == 2


@pytest.mark.parametrize(
    "mention,shown",
    [("</wizards:1>", "</wizards:1>"), (None, "`/wizards`")],
    ids=["mention", "fallback"],
)
async def test_lockdown_start_stops_near_token_expiry(
    cog: admin_module.AdminCog,
    bot: MockBot,
    ctx: MockCtx,
    mock_sleep: AsyncMock,
    mention: str | None,
    shown: str,
):
    """Near the interaction's expiry, the report stops and points to /wizards."""
    bot.cmd_mention.return_value = mention
    ctx.interaction.created_at -= admin_module.TOKEN_LIFETIME
    with running_wizards(2, 0):
        await start(cog, ctx)

    timeout = f"-# Hit the time limit. Run {shown} to check manually."
    assert edits(ctx) == [f"{header(bot)}\n**Wizards running:** 2\n{timeout}"]
    bot.cmd_mention.assert_called_once_with("wizards")
    mock_sleep.assert_not_awaited()


@pytest.mark.parametrize(
    "interrupt",
    [
        lambda bot: bot.end_lockdown(),
        lambda bot: bot.start_lockdown(LockdownReason.MAINTENANCE),
    ],
    ids=["ended", "replaced"],
)
async def test_lockdown_start_stops_when_superseded(
    cog: admin_module.AdminCog,
    bot: MockBot,
    ctx: MockCtx,
    mock_sleep: AsyncMock,
    interrupt: Callable[[MockBot], object],
):
    """Ending or replacing the lockdown stops the old wizard report."""
    mock_sleep.side_effect = lambda _: interrupt(bot)
    with running_wizards(2, 0):
        await start(cog, ctx)

    assert len(edits(ctx)) == 1
    assert edits(ctx)[0].endswith("**Wizards running:** 2")


async def test_lockdown_end(
    cog: admin_module.AdminCog, bot: MockBot, ctx: MockCtx, mock_sleep: AsyncMock
):
    """Ending a lockdown clears it."""
    with running_wizards(0):
        await start(cog, ctx)
    ctx.respond.reset_mock()

    await cog.lockdown_end.callback(cog, ctx)

    assert bot.lockdown is None
    ctx.respond.assert_awaited_once_with("Removed lockdown.", ephemeral=True)
