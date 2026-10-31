"""interface/motd.py - Show the Message of the Day after commands."""

import asyncio
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from loguru import logger

from ctx import AppCtx
from utils import cmd_replace_respond

if TYPE_CHECKING:
    from bot import InconnuBot

# Commands that shouldn't show the MOTD
MOTD_EXEMPT = frozenset({"motd", "announce"})


class MotDCog(commands.Cog):
    """Shows each user the MOTD once, after their next command."""

    def __init__(self, bot: InconnuBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_application_command(self, ctx: AppCtx):
        """Show the MOTD once per user."""
        if ctx.command is None:
            return
        if self.bot.motd is None or ctx.command.qualified_name in MOTD_EXEMPT:
            return
        if ctx.user.id in self.bot.motd_given:
            return

        logger.debug("Showing MOTD to {}", ctx.user.name)
        await asyncio.sleep(1)
        try:
            await cmd_replace_respond(ctx, embed=self.bot.motd, ephemeral=True)
            self.bot.motd_given.add(ctx.user.id)
        except discord.HTTPException:
            logger.warning("Could not show MOTD to {}", ctx.user.name)


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(MotDCog(bot))
