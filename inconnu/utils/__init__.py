"""Commonly used utilities."""

import re

import discord
from discord.ext import commands

import inconnu
from config import SUPPORTER_GUILD, SUPPORTER_ROLE
from inconnu import errors
from inconnu.utils.cmdreplace import cmd_replace
from inconnu.utils.decorators import not_on_lockdown
from inconnu.utils.error import ErrorEmbed, error
from inconnu.utils.haven import Haven
from inconnu.utils.paramparse import parse_parameters
from logger import Logger


def clean_text(text: str) -> str:
    """Remove extra spaces in text."""
    return " ".join(text.split())


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


def is_admin(ctx, owner_id=None):
    """
    Check if the ctx user is an admin.
    If owner is set, checks if it and ctx.user are equal.
    """
    if owner_id == ctx.user.id:
        return True
    if isinstance(ctx.channel, discord.PartialMessageable):
        # We can't use permissions_for
        user = ctx.user
        return user.top_role.permissions.administrator or user.guild_permissions.administrator
    return ctx.channel.permissions_for(ctx.user).administrator


def is_supporter(ctx, user: discord.Member = None) -> bool:
    """Returns True if the user invoking the command is a supporter."""
    support_server = inconnu.bot.get_guild(SUPPORTER_GUILD)
    user = user or ctx.user

    # First, see if the invoker is on the support server
    if (member := support_server.get_member(user.id)) is not None:
        Logger.debug(
            "SUPPORTER: %s#%s is on %s", user.name, user.discriminator, support_server.name
        )
        if member.get_role(SUPPORTER_ROLE) is not None:
            Logger.debug("SUPPORTER: %s#%s is a supporter", user.name, user.discriminator)
            return True
        Logger.debug("SUPPORTER: %s#%s is a not a supporter", user.name, user.discriminator)
        return False
    Logger.debug("SUPPORTER: %s#%s is not on the support server", user.name, user.discriminator)
    return False


def _check_supporter(ctx, user: discord.Member = None):
    """Wraps is_supporter() to raise on failure."""
    if not ctx.bot.welcomed:
        command = ctx.bot.cmd_mention(ctx.command.qualified_name)
        raise inconnu.errors.NotReady(
            (
                f"{ctx.bot.user.mention} is currently rebooting. "
                f"{command} will be available in a few minutes."
            )
        )

    if not is_supporter(ctx, user):
        raise errors.NotPremium()
    return True


def has_premium():
    """A decorator for commands that only work for supporters."""
    return commands.check(_check_supporter)


def pull_mentions(text: str) -> set[str]:
    """Pulls mentions from text."""
    mentions = re.findall(r"(<(?:@|@&|#)\d{1,30}>)", text)
    return set(mentions)


class VCharEmbed(discord.Embed):
    """A standardized VChar display."""

    def __init__(self, ctx, character, owner: discord.Member = None, **kwargs):
        owner = owner or ctx.user
        show_thumbnail = kwargs.pop("show_thumbnail", True)

        if "title" in kwargs:
            author_name = character.name
        else:
            author_name = owner.name
            kwargs["title"] = character.name

        if is_supporter(ctx, owner):
            # Premium color
            kwargs["color"] = 0x00A4FF

        super().__init__(**kwargs)

        self.set_author(name=author_name, icon_url=inconnu.get_avatar(owner))

        if show_thumbnail:
            self.set_thumbnail(url=character.profile_image_url)
