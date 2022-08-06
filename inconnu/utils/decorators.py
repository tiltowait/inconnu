"""Command decorators."""

from discord.ext import commands

import inconnu
from logger import Logger


def not_on_lockdown():
    """A decorator that checks if the bot is on lockdown."""

    def predicate(ctx):
        if ctx.bot.lockdown is not None:
            Logger.info(
                "BOT: %s#%s (%s) attempted locked-down command",
                ctx.user.name,
                ctx.user.discriminator,
                ctx.guild.name,
            )
            raise inconnu.errors.LockdownError()
        Logger.debug("BOT: Not on lockdown")
        return True

    return commands.check(predicate)
