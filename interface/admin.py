"""Admin commands."""
# pylint: disable=no-self-use

import asyncio
from datetime import timedelta

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from config import ADMIN_GUILD


class AdminCog(commands.Cog):
    """A cog with various administrative commands."""

    @discord.slash_command(guild_ids=[ADMIN_GUILD])
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    async def announce(
        self,
        ctx: discord.ApplicationContext,
        title: Option(str, "The message's title"),
        description: Option(str, "The message's main content"),
        field1_name: Option(str, "The name of the first field", required=False),
        field1_value: Option(str, "The first field's contents", required=False),
        field2_name: Option(str, "The name of the first field", required=False),
        field2_value: Option(str, "The first field's contents", required=False),
    ):
        """Set the Message of the Day."""
        title = " ".join(title.split())
        description = " ".join(description.split())

        if not (title and description):
            await ctx.respond("`title` and `content` can't be empty!", ephemeral=True)
            return

        embed = discord.Embed(title=title, description=description)
        embed.set_author(name="Announcement", icon_url=ctx.bot.user.display_avatar)
        embed.set_footer(text="This is a one-time message. To see it again, use /motd.")

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
            ctx.bot.set_motd(embed)
            await ctx.respond("Announcement set!", ephemeral=True)

        except AttributeError:
            await ctx.respond("A field must have an associated value!", ephemeral=True)

    @discord.slash_command(guild_ids=[ADMIN_GUILD])
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    async def unannounce(self, ctx: discord.ApplicationContext):
        """Unset the Message of the Day."""
        ctx.bot.set_motd(None)
        await ctx.respond("Message of the Day unset!", ephemeral=True)

    @discord.slash_command()
    async def motd(self, ctx: discord.ApplicationContext):
        """Show the Message of the Day."""
        if ctx.bot.motd is not None:
            await ctx.respond(embed=ctx.bot.motd, ephemeral=True)
        else:
            await ctx.respond("No Message of the Day is set.", ephemeral=True)

    @discord.slash_command(guild_ids=[ADMIN_GUILD])
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    async def shutdown(self, ctx: discord.ApplicationContext):
        """Shuts down the bot after 15 minutes."""
        await ctx.respond("Preparing to shut down.", ephemeral=True)
        ctx.bot.lockdown = discord.utils.utcnow() + timedelta(minutes=15)

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
        if message is not None:
            await message.edit(msg)
        else:
            await ctx.respond(msg, ephemeral=True)

        logger.info("SHUTDOWN: Bot is ready for shutdown")


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(AdminCog(bot))
