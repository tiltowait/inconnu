"""Admin commands."""

import asyncio
from datetime import timedelta

import discord
from discord.ext import commands

import inconnu
from logger import Logger

# pylint: disable=no-self-use


class AdminCog(commands.Cog):
    """A cog with various administrative commands."""

    WHITELIST = [826628660450689074, 935219170176532580]

    @discord.slash_command(guild_ids=WHITELIST)
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    async def shutdown(self, ctx: discord.ApplicationContext):
        """Shuts down the bot after 15 minutes."""
        ctx.bot.lockdown = discord.utils.utcnow() + timedelta(minutes=15)
        timestamp = inconnu.gen_timestamp(ctx.bot.lockdown, "R")

        await ctx.respond(
            (
                f"**NOTICE:** {ctx.bot.user.mention} will shut down {timestamp}. "
                "Certain commands may be unavailable."
            )
        )

        message = None
        while ctx.bot.wizards > 0:
            if ctx.bot.wizards > 1:
                # Properly pluralize the message
                is_are = "are"
                wizards = "chargen wizards"
            else:
                is_are = "is"
                wizards = "chargen wizard"
            msg = f"There {is_are} **{ctx.bot.wizards}** {wizards} running."

            if message is None:
                message = await ctx.respond(msg, ephemeral=True)
            else:
                message.edit(content=msg)
            await asyncio.sleep(15)

        msg = f"{ctx.bot.user.mention} can restart now. No chargen wizards are running."
        if message is None:
            await message.edit(msg)
        else:
            await ctx.respond(msg, ephemeral=True)

        Logger.info("SHUTDOWN: Bot is ready for shutdown")

    @discord.slash_command(guild_ids=WHITELIST)
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    async def purge(self, ctx: discord.ApplicationContext):
        """Purge the character cache."""
        inconnu.char_mgr.purge()
        await ctx.respond("Character cache purged.", ephemeral=True)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(AdminCog(bot))
