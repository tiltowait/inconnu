"""Command decorators."""

import discord
from discord.ext import commands

import inconnu
from config import SUPPORTER_GUILD
from logger import Logger


def not_on_lockdown():
    """A decorator that checks if the bot is on lockdown."""

    def predicate(ctx):
        if ctx.bot.lockdown is not None:
            Logger.info("BOT: %s (%s) attempted locked-down command", ctx.user.name, ctx.guild.name)
            raise inconnu.errors.LockdownError()
        Logger.debug("BOT: Not on lockdown")
        return True

    return commands.check(predicate)


def _check_supporter(ctx, user: discord.Member = None):
    """Wraps is_supporter() to raise on failure."""

    def raise_not_ready():
        command = ctx.bot.cmd_mention(ctx.command.qualified_name)
        raise inconnu.errors.NotReady(
            (
                f"{ctx.bot.user.mention} is currently rebooting. "
                f"{command} will be available in a few minutes."
            )
        )

    # Waiting for the bot to be fully ready takes about 15 minutes. To speed
    # this up, we try to fetch supporter status as soon as it's available
    # instead of waiting for on_ready().
    if ctx.bot.get_guild(SUPPORTER_GUILD) is None:
        if not ctx.bot.welcomed:
            raise_not_ready()
        else:
            raise LookupError("Inconnu's support server is not configured!")

    if not inconnu.utils.is_supporter(ctx, user):
        if not ctx.bot.welcomed:
            # Support server members may still be fetching
            raise_not_ready()

        # User is definitively not a supporter
        raise inconnu.errors.NotPremium

    return True


def premium():
    """A decorator for commands that only work for supporters."""
    return commands.check(_check_supporter)
