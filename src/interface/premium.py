"""interface/premium.py - Track supporter status changes."""

from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from loguru import logger

from config import settings
from services import premium

if TYPE_CHECKING:
    from bot import InconnuBot


class PremiumCog(commands.Cog):
    """Watches the supporter guild for supporter role changes."""

    def __init__(self, bot: "InconnuBot"):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Check for supporter status changes."""
        if after.guild.id != settings.supporter_guild:
            return

        was_supporter = premium.is_supporter(before)
        is_supporter = premium.is_supporter(after)

        if was_supporter and not is_supporter:
            logger.info("{} is no longer a supporter", after.name)
            await premium.mark_lost(after)
        elif is_supporter and not was_supporter:
            logger.info("{} is now a supporter!", after.name)
            await self._mark_gained(after)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Restore a returning supporter's status."""
        if member.guild.id == settings.supporter_guild and premium.is_supporter(member):
            await self._mark_gained(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """A supporter who leaves the supporter guild loses their status."""
        if member.guild.id == settings.supporter_guild and premium.is_supporter(member):
            await premium.mark_lost(member)

    async def _mark_gained(self, member: discord.Member):
        """Mark premium gain, pointing the member to the image upload command."""
        await premium.mark_gained(member, self.bot.cmd_mention("character image upload"))


def setup(bot: "InconnuBot"):
    """Add the cog to the bot."""
    bot.add_cog(PremiumCog(bot))
