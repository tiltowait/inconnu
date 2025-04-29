"""Command decorators."""

import discord
from discord.ext import commands

import inconnu
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


async def _check_supporter(ctx: discord.ApplicationContext, user: discord.Member | None = None):
    """Wraps is_supporter() to raise on failure."""
    if not await inconnu.utils.get_or_fetch_supporter(ctx, user):
        raise inconnu.errors.NotPremium

    return True


def premium():
    """A decorator for commands that only work for supporters."""
    return commands.check(_check_supporter)
