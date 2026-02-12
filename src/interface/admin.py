"""Admin commands."""

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord import option
from discord.ext import commands
from loguru import logger

import services
from config import ADMIN_GUILD
from ctx import AppCtx

if TYPE_CHECKING:
    from bot import InconnuBot


class AdminCog(commands.Cog):
    """A cog with various administrative commands."""

    def __init__(self, bot: "InconnuBot"):
        self.bot = bot

    @discord.slash_command(guild_ids=[ADMIN_GUILD])
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    @option("title", description="The message's title")
    @option("description", description="The message's main content")
    @option("field1_name", description="The name of the first field", required=False)
    @option("field1_value", description="The first field's contents", required=False)
    @option("field2_name", description="The name of the first field", required=False)
    @option("field2_value", description="The first field's contents", required=False)
    async def announce(
        self,
        ctx: discord.ApplicationContext,
        title: str,
        description: str,
        field1_name: str,
        field1_value: str,
        field2_name: str,
        field2_value: str,
    ):
        """Set the Message of the Day."""
        title = " ".join(title.split())
        description = " ".join(description.split())

        if not (title and description):
            await ctx.respond("`title` and `content` can't be empty!", ephemeral=True)
            return

        embed = discord.Embed(title=title, description=description)
        embed.set_footer(text="This is a one-time message. To see it again, use /motd.")
        if self.bot.user is not None:
            embed.set_author(name="Announcement", icon_url=self.bot.user.display_avatar)

        try:
            for field, value in [
                (field1_name, field1_value),
                (field2_name, field2_value),
            ]:
                if field:
                    field = " ".join(field.split())
                    value = " ".join(value.split())
                    if not (field and value):
                        await ctx.respond("Field names and values can't be empty!", ephemeral=True)
                        return
                    embed.add_field(name=field, value=value, inline=False)

            # Set the MotD
            self.bot.set_motd(embed)
            await ctx.respond("Announcement set!", ephemeral=True)

        except AttributeError:
            await ctx.respond("A field must have an associated value!", ephemeral=True)

    @discord.slash_command(guild_ids=[ADMIN_GUILD])
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    async def unannounce(self, ctx: discord.ApplicationContext):
        """Unset the Message of the Day."""
        self.bot.set_motd(None)
        await ctx.respond("Message of the Day unset!", ephemeral=True)

    @discord.slash_command()
    async def motd(self, ctx: discord.ApplicationContext):
        """Show the Message of the Day."""
        if self.bot.motd is not None:
            await ctx.respond(embed=self.bot.motd, ephemeral=True)
        else:
            await ctx.respond("No Message of the Day is set.", ephemeral=True)

    @discord.slash_command(guild_ids=[ADMIN_GUILD])
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    async def wizards(self, ctx: AppCtx):
        """Show the number of character wizards running."""
        await ctx.respond(f"**Wizards running:** {services.wizard_cache.count}", ephemeral=True)

    @discord.slash_command(guild_ids=[ADMIN_GUILD])
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    async def shutdown(self, ctx: discord.ApplicationContext):
        """Shuts down the bot after 15 minutes."""
        await ctx.respond("Preparing to shut down.", ephemeral=True)
        self.bot.lockdown = discord.utils.utcnow() + timedelta(minutes=15)

        message = None
        while services.wizard_cache.count > 0:
            if services.wizard_cache.count > 1:
                # Properly pluralize the message
                is_are = "are"
                wizards = "chargen wizards"
            else:
                is_are = "is"
                wizards = "chargen wizard"
            msg = f"There {is_are} **{services.wizard_cache.count}** {wizards} running."

            if message is None:
                message = await ctx.respond(msg, ephemeral=True)
            else:
                message.edit(content=msg)
            await asyncio.sleep(15)

        if self.bot.user is not None:
            msg = f"{self.bot.user.mention} can restart now. No chargen wizards are running."
            if message is not None:
                await message.edit(msg)
            else:
                await ctx.respond(msg, ephemeral=True)

        logger.info("SHUTDOWN: Bot is ready for shutdown")


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(AdminCog(bot))
