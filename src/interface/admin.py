"""Admin commands."""

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands
from loguru import logger

import services
from config import settings
from ctx import AppCtx
from services.lockdown import LockdownReason

if TYPE_CHECKING:
    from bot import InconnuBot

WIZARD_POLL = timedelta(seconds=15)
# Edits go through the interaction token, which expires after 15 minutes
TOKEN_LIFETIME = timedelta(minutes=15)


class AdminCog(commands.Cog):
    """A cog with various administrative commands."""

    lockdown = SlashCommandGroup(
        "lockdown",
        "Warn users of an upcoming shutdown.",
        guild_ids=[settings.admin_server],
        default_member_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: InconnuBot):
        self.bot = bot

    @discord.slash_command(guild_ids=[settings.admin_server])
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
        ctx: AppCtx,
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
            for field, value in (
                (field1_name, field1_value),
                (field2_name, field2_value),
            ):
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

    @discord.slash_command(guild_ids=[settings.admin_server])
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    async def unannounce(self, ctx: AppCtx):
        """Unset the Message of the Day."""
        self.bot.set_motd(None)
        await ctx.respond("Message of the Day unset!", ephemeral=True)

    @discord.slash_command(guild_ids=[settings.admin_server])
    @discord.default_permissions(administrator=True)
    @commands.is_owner()
    async def wizards(self, ctx: AppCtx):
        """Show the number of character wizards running."""
        await ctx.respond(f"**Wizards running:** {services.wizard_cache.count}", ephemeral=True)

    @lockdown.command(name="start")
    @commands.is_owner()
    @option("reason", description="Why the bot is going down", choices=list(LockdownReason))
    async def lockdown_start(self, ctx: AppCtx, reason: str):
        """Put the bot in lockdown, then report running chargen wizards until none remain."""
        lockdown = self.bot.start_lockdown(LockdownReason(reason))
        header = f"Lockdown set for {discord.utils.format_dt(lockdown.shutdown_time, 't')}."
        await ctx.respond(header, ephemeral=True)

        # Two polls of margin guarantee the last edit lands before expiry
        deadline = ctx.interaction.created_at + TOKEN_LIFETIME - 2 * WIZARD_POLL
        while (count := services.wizard_cache.count) > 0:
            running = f"{header}\n**Wizards running:** {count}"
            if discord.utils.utcnow() >= deadline:
                wizards = self.bot.cmd_mention("wizards") or "`/wizards`"
                await ctx.edit(
                    content=f"{running}\n-# Hit the time limit. Run {wizards} to check manually."
                )
                return

            await ctx.edit(content=running)
            await asyncio.sleep(WIZARD_POLL.total_seconds())
            if self.bot.lockdown is not lockdown:
                # Ended, or replaced by a newer lockdown that reports on its own
                return

        await ctx.edit(content=f"{header}\n{self.bot.me.display_name} can restart now.")
        logger.info("Bot is ready for shutdown")

    @lockdown.command(name="end")
    @commands.is_owner()
    async def lockdown_end(self, ctx: AppCtx):
        """Remove the lockdown."""
        self.bot.end_lockdown()
        await ctx.respond("Removed lockdown.", ephemeral=True)


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(AdminCog(bot))
