"""interface/guildcache.py - Keep the guild cache in sync with Discord."""

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from services import guild_cache

if TYPE_CHECKING:
    from bot import InconnuBot


class GuildCacheCog(commands.Cog):
    """Populates the guild cache and mirrors guild and member changes into it."""

    def __init__(self, bot: "InconnuBot"):
        self.bot = bot
        self.refreshed = False

    @commands.Cog.listener()
    async def on_ready(self):
        """Populate the cache on first connection."""
        if not self.refreshed:
            await guild_cache.refresh(self.bot.guilds)
            self.refreshed = True

    # Guilds

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Add the guild to the cache."""
        if await guild_cache.ready():
            await guild_cache.upsert_guilds(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Remove the guild from the cache."""
        if await guild_cache.ready():
            await guild_cache.delete_guild(guild)

    @commands.Cog.listener()
    async def on_guild_update(self, _: discord.Guild, after: discord.Guild):
        """Update the guild's name and icon in the cache."""
        if await guild_cache.ready():
            await guild_cache.upsert_guilds(after)

    # Members

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Add the member to the cache."""
        if await guild_cache.ready():
            await guild_cache.upsert_members(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Remove the member from the cache."""
        if await guild_cache.ready():
            await guild_cache.delete_member(member)

    @commands.Cog.listener()
    async def on_member_update(self, _: discord.Member, after: discord.Member):
        """Update the member in the cache."""
        if await guild_cache.ready():
            await guild_cache.upsert_members(after)


def setup(bot: "InconnuBot"):
    """Add the cog to the bot."""
    bot.add_cog(GuildCacheCog(bot))
