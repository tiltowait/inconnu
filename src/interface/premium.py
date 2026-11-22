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

    def __init__(self, bot: InconnuBot):
        self.bot = bot

    # _raw_ listeners don't need the caches, so we can catch supporter changes
    # while the bot is still starting up.

    @commands.Cog.listener()
    async def on_raw_member_update(self, payload: discord.RawMemberUpdateEvent):
        """Check for supporter status changes."""
        if payload.guild_id != settings.supporter_guild:
            return

        was_supporter = premium.is_supporter(payload.user_id)
        is_supporter = settings.supporter_role in map(int, payload.data["roles"])

        if was_supporter and not is_supporter:
            logger.info("{} is no longer a supporter", payload.member.name)
            await premium.mark_lost(payload.member)
        elif is_supporter and not was_supporter:
            logger.info("{} is now a supporter!", payload.member.name)
            await premium.mark_gained(payload.member, self.bot)

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        """A supporter who leaves the supporter guild loses their status."""
        if payload.guild_id == settings.supporter_guild and premium.is_supporter(payload.user.id):
            await premium.mark_lost(payload.user)


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(PremiumCog(bot))
