"""Which commands only Storytellers may use.

For most of these, the @decorators.storyteller() check is the only guard, so
losing it would let any player use them."""

from collections.abc import Iterator

import discord

from bot import InconnuBot
from utils.decorators import _storyteller_check

STORYTELLER_COMMANDS = {
    "bulk award xp",
    "experience remove entry",
    "transfer",
    "Toggle Roll Statistics",
}


def walk_commands(bot: InconnuBot) -> Iterator[discord.ApplicationCommand]:
    """Every command and subcommand. The bot hasn't synced, so they're still
    pending (walk_application_commands() only sees synced ones)."""
    for command in bot.pending_application_commands:
        if isinstance(command, discord.SlashCommandGroup):
            yield from command.walk_commands()
        yield command


def test_storyteller_commands(shared_bot: InconnuBot):
    """Exactly the expected commands carry the Storyteller check. Update the
    list when a command gains or loses it."""
    guarded = {
        getattr(command, "qualified_name", command.name)
        for command in walk_commands(shared_bot)
        if _storyteller_check in command.checks
    }
    assert guarded == STORYTELLER_COMMANDS
