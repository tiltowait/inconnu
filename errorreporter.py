"""An error reporter."""

import os
import traceback

import discord
import pymongo.errors
from discord.ext import commands

import inconnu
from logger import Logger


class ErrorReporter:
    """A utility that posts error messages in a specified channel."""

    def __init__(self):
        self.bot = None
        self.channel = None

    async def prepare_channel(self, bot):
        """Attempt to get the error channel from the bot."""
        self.bot = bot
        try:
            if (channel := os.getenv("REPORT_CHANNEL")) is not None:
                if (channel := await bot.fetch_channel(int(channel))) is not None:
                    Logger.info("REPORTER: Recording errors in #%s", channel.name)
                    self.channel = channel
                else:
                    Logger.warning("REPORTER: Unhandled exceptions channel invalid")
            else:
                Logger.warning("REPORTER: Unhandled exceptions report channel not set")
        except ValueError:
            Logger.warning("REPORTER: Unhandled exceptions channel is not an int")

    async def report_error(self, ctx: discord.ApplicationContext | discord.Interaction, error):
        """Report an error, switching between known and unknown."""
        error = getattr(error, "original", error)
        if isinstance(ctx, discord.ApplicationContext):
            respond = ctx.respond
        else:
            if ctx.response.is_done():
                respond = ctx.followup.send
            else:
                respond = ctx.response.send_message

        # Known exceptions

        if isinstance(error, commands.NoPrivateMessage):
            await respond("Sorry, this command can only be run in a server!", ephemeral=True)
            return
        if isinstance(error, commands.MissingPermissions):
            await respond("Sorry, you don't have permission to do this!", ephemeral=True)
            return
        if isinstance(error, discord.errors.NotFound):
            # This just means a button tried to disable when its message no longer exists.
            # We don't care, and there's nothing we can do about it anyway.
            return
        if isinstance(error, inconnu.errors.NotReady):
            await inconnu.utils.error(ctx, str(error), title="One moment, please")
            return
        if isinstance(error, inconnu.errors.NotPremium):
            troubleshoot_url = (
                "https://docs.inconnu.app/advanced/troubleshooting#you-arent-able-to-upload-images"
            )

            cmd_mention = ctx.bot.cmd_mention(ctx.command.qualified_name)
            await inconnu.utils.error(
                ctx,
                (
                    f"Only patrons can use {cmd_mention}. "
                    "Click the Patreon button to get started!"
                ),
                (
                    "Already a patron?",
                    f"[Check the troubleshooting page.]({troubleshoot_url})",
                ),
                title="Premium feature",
                help="https://docs.inconnu.app/guides/premium",
            )
            return
        if isinstance(error, commands.NotOwner):
            await respond(
                f"Sorry, only {ctx.bot.user.mention}'s owner may issue this command!",
                ephemeral=True,
            )
            return
        if isinstance(error, inconnu.errors.LockdownError):
            timestamp = inconnu.gen_timestamp(ctx.bot.lockdown, "R")
            err = f"{ctx.bot.user.mention} is undergoing maintenance {timestamp}."
            embed = inconnu.utils.ErrorEmbed(
                ctx.user,
                err,
                title="Command temporarily unavailable",
                footer="Sorry for any inconvenience.",
            )
            await respond(embed=embed, ephemeral=True)
            return
        if isinstance(error, inconnu.errors.HandledError):
            Logger.debug("REPORTER: Ignoring a HandledError")
            return
        if isinstance(error, discord.errors.DiscordServerError):
            # There's nothing we can do about these
            Logger.error("REPORTER: Discord server error detected")
            return

        # Unknown errors and database errors are logged to a channel

        if isinstance(error, pymongo.errors.PyMongoError):
            await inconnu.log.report_database_error(self.bot, ctx)

        # Unknown exceptions
        embed = await self.error_embed(ctx, error)
        try:
            await self._report_unknown_error(respond, embed)
        except discord.HTTPException:
            embed.description = "The error was too long to fit! Check the logs."
            await self._report_unknown_error(respond, embed)
            raise error from error

        # Print the error to the log
        if isinstance(ctx, discord.ApplicationContext):
            scope = ctx.command.qualified_name.upper()
        else:
            scope = "INTERACTION"
        formatted = "".join(traceback.format_exception(error))
        Logger.error("%s: %s", scope, formatted)

    async def _report_unknown_error(self, respond, embed):
        """Report an unknown exception."""
        user_msg = f"{self.bot.user.mention} has encountered an error. Support has been notified!"

        try:
            await respond(user_msg, ephemeral=True)
        except (discord.NotFound, discord.HTTPException) as err:
            Logger.error("REPORTER: Couldn't inform user of an error: %s", str(err))
        finally:
            if self.channel is not None:
                await self.channel.send(embed=embed)

    @staticmethod
    async def error_embed(ctx, error) -> discord.Embed:
        """Create an error embed."""
        if "50027" in str(error):
            description = "**Unrecoverable Discord error:** Invalid webhook token"
            await ctx.channel.send(
                (
                    "**Alert:** A Discord issue is currently impacting {self.bot.user.mention}'s "
                    "responsiveness. Check status here: https://discordstatus.com"
                ),
                delete_after=15,
            )
        else:
            description = "\n".join(traceback.format_exception(error))

        # If we can, we use the command name to try to pinpoint where the error
        # took place. The stack trace usually makes this clear, but not always!
        if isinstance(ctx, discord.ApplicationContext):
            command_name = ctx.command.qualified_name.upper()
        else:
            command_name = "INTERACTION"

        error_name = type(error).__name__

        embed = discord.Embed(
            title=f"{command_name}: {error_name}",
            description=description,
            color=0xFF0000,
            timestamp=discord.utils.utcnow(),
        )

        if ctx.guild is not None:
            guild_name = ctx.guild.name
            guild_icon = ctx.guild.icon or ""
        else:
            guild_name = "DM"
            guild_icon = ""

        embed.set_author(name=f"{ctx.user.name} on {guild_name}", icon_url=guild_icon)

        return embed


reporter = ErrorReporter()
