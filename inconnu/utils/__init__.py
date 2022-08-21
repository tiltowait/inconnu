"""Commonly used utilities."""

import discord
from discord.ext import commands

import inconnu
from config import SUPPORTER_GUILD, SUPPORTER_ROLE
from inconnu import errors
from logger import Logger

from .decorators import not_on_lockdown
from .error import ErrorEmbed, error
from .haven import Haven
from .paramparse import parse_parameters


def raw_command_options(interaction) -> str:
    """Get the options in a command as a dict."""
    options = {}
    for option in interaction.data.get("options", []):
        name = option["name"]
        value = option["value"]
        options[name] = value

    return options


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


def is_supporter(ctx, user: discord.Member = None) -> bool:
    """Returns True if the user invoking the command is a supporter."""
    support_server = ctx.bot.get_guild(SUPPORTER_GUILD)
    user = user = ctx.user

    # First, see if the invoker is on the support server
    if (member := support_server.get_member(user.id)) is not None:
        Logger.debug(
            "SUPPORTER: %s#%s is on %s", member.name, member.discriminator, support_server.name
        )
        if member.get_role(SUPPORTER_ROLE) is not None:
            Logger.info("SUPPORTER: %s#%s is a supporter", member.name, member.discriminator)
            return True
        Logger.info("SUPPORTER: %s#%s is a not a supporter", member.name, member.discriminator)
        raise errors.NotPremium()
    Logger.debug("SUPPORTER: %s#%s is not on the support server", member.name, member.discriminator)
    raise errors.NotPremium()


def has_premium():
    """A decorator for commands that only work for supporters."""
    return commands.check(is_supporter)


class VCharEmbed(discord.Embed):
    """A standardized VChar display."""

    def __init__(self, ctx, character, owner: discord.Member = None, **kwargs):
        owner = owner or ctx.user
        show_thumbnail = kwargs.pop("show_thumbnail", True)
        title = kwargs.pop("title", character.name)

        if is_supporter(ctx, owner):
            # Premium color
            kwargs["color"] = 0x00A4FF

        super().__init__(title=title, **kwargs)
        self.set_author(name=owner.name, icon_url=inconnu.get_avatar(owner))

        if show_thumbnail:
            self.set_thumbnail(url=character.profile_image_url)
