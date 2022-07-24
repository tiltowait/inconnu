"""Commonly used utilities."""

from discord.ext import commands

import config
from inconnu import errors
from logger import Logger

from .error import ErrorEmbed, error
from .haven import Haven
from .paramparse import parse_parameters


def command_options(interaction) -> str:
    """Format the command options for easy display."""
    options = []
    for option in interaction.data.get("options", []):
        _name = option["name"]
        _value = option["value"]

        # This is hardly exhaustive, since option types can also be members
        # or channels, but the main purpose with enclosing strings in quotes
        # is to remove ambiguity that might occur with more complex string
        # patterns.
        if isinstance(_value, str):
            options.append(f'{_name}="{_value}"')
        else:
            options.append(f"{_name}={_value}")

    return ", ".join(options) if options else "None"


def is_supporter(ctx) -> bool:
    """Returns True if the user invoking the command is a supporter."""
    support_server = ctx.bot.get_guild(config.supporter_server)

    # First, see if the invoker is on the support server
    if (member := support_server.get_member(ctx.user.id)) is not None:
        Logger.debug(
            "SUPPORTER: %s#%s is on %s", member.name, member.discriminator, support_server.name
        )
        if member.get_role(config.supporter_role) is not None:
            Logger.info("SUPPORTER: %s#%s is a supporter", member.name, member.discriminator)
            return True
        Logger.info("SUPPORTER: %s#%s is a not a supporter", member.name, member.discriminator)
        raise errors.NotPremium()
    Logger.debug("SUPPORTER: %s#%s is not on the support server", member.name, member.discriminator)
    raise errors.NotPremium()


def has_premium():
    """A decorator for commands that only work for supporters."""
    return commands.check(is_supporter)
