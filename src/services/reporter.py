"""An error reporter."""

import traceback
from datetime import datetime
from typing import TYPE_CHECKING

import discord
import pymongo.errors
from discord.ext import commands
from loguru import logger

import constants
import errors
import ui
from config import settings
from ctx import AppInvocation
from services.log import report_database_error
from utils.urls import docs_url

if TYPE_CHECKING:
    from bot import InconnuBot

MAX_DESCRIPTION = 4096  # Discord's embed description limit
INVALID_WEBHOOK_TOKEN = 50027  # Discord error code


def error_scope(ctx: AppInvocation) -> str:
    """The command the error happened in, or INTERACTION for components and the like. The
    stack trace usually makes this clear, but not always!"""
    if isinstance(ctx, discord.ApplicationContext) and ctx.command is not None:
        return ctx.command.qualified_name.upper()
    return "INTERACTION"


class ErrorReporter:
    """A utility that posts error messages in a specified channel."""

    def __init__(self):
        self._bot: InconnuBot | None = None
        self.channel: discord.TextChannel | None = None

    @property
    def bot(self) -> InconnuBot:
        """The bot instance."""
        if self._bot is None:
            raise RuntimeError("prepare_channel() must be called first")
        return self._bot

    @property
    def reinvite_message(self) -> discord.Embed:
        """Instructions for re-inviting the bot and submitting a bug report."""
        invite = self.bot.invite_url
        embed = discord.Embed(
            title="Please re-invite Inconnu",
            description=(
                f"**Inconnu** has encountered an error. [Re-inviting]({invite}) "
                "the bot may fix it. No character data/settings will be lost."
            ),
            color=discord.Color.red(),
        )
        embed.add_field(
            name="If that doesn't work ...",
            value=(
                f"Please join [the support server]({constants.SUPPORT_URL}) "
                "and file a bug report. Thank you!"
            ),
        )
        return embed

    async def prepare_channel(self, bot: InconnuBot):
        """Attempt to get the error channel from the bot."""
        self._bot = bot
        if settings.report_channel is None:
            logger.warning("Unhandled exceptions report channel not set")
            return

        logger.info("Report channel ID: {}", settings.report_channel)
        try:
            channel = await bot.fetch_channel(settings.report_channel)
        except (discord.HTTPException, discord.InvalidData) as err:
            logger.warning("Couldn't fetch the report channel: {}", str(err))
            return

        if isinstance(channel, discord.TextChannel):
            logger.info("Recording errors in #{}", channel.name)
            self.channel = channel
        else:
            logger.warning("Unhandled exceptions channel invalid")

    async def report_error(self, ctx: AppInvocation, error: Exception):
        """Report an error, switching between known and unknown."""
        error = getattr(error, "original", error)

        match error:
            case commands.NoPrivateMessage():
                await ctx.respond(
                    "Sorry, this command can only be run in a server!", ephemeral=True
                )
            case commands.MissingPermissions():
                await ctx.respond("Sorry, you don't have permission to do this!", ephemeral=True)
            case discord.NotFound() | errors.HandledError():
                # NotFound just means a button tried to disable when its message no longer
                # exists. We don't care, and there's nothing we can do about it anyway.
                pass
            case errors.NotReady():
                await ui.embeds.error(ctx, str(error), title="One moment, please")
            case errors.NotPremium():
                await self._report_not_premium(ctx)
            case commands.NotOwner():
                await ctx.respond(
                    f"Sorry, only {ctx.bot.me.mention}'s owner may issue this command!",
                    ephemeral=True,
                )
            case errors.LockdownError() if ctx.bot.lockdown:
                await self._report_lockdown(ctx, ctx.bot.lockdown)
            case errors.InvalidAttachment():
                await ui.embeds.error(ctx, str(error), title="Invalid file")
            case discord.DiscordServerError():
                # There's nothing we can do about these
                logger.error("Discord server error detected")
            case AttributeError() if "PartialMessageable" in str(error):
                logger.opt(exception=error).warning("Got a PartialMessageable in an error.")
                await ctx.respond(embed=self.reinvite_message)
            case discord.HTTPException() if error.code == INVALID_WEBHOOK_TOKEN:
                # A Discord issue, but we still want to know about it
                await self._outage_alert(ctx)
                await self._report_unknown(ctx, error)
            case _:
                await self._report_unknown(ctx, error)

    async def _report_not_premium(self, ctx: AppInvocation):
        """Tell the user the feature requires premium."""
        troubleshoot_url = docs_url("advanced/troubleshooting#you-arent-able-to-upload-images")

        if ctx.command is not None:
            cmd_mention = ctx.bot.cmd_mention(ctx.command.qualified_name)
        else:
            cmd_mention = "this feature"
        await ui.embeds.error(
            ctx,
            (f"Only patrons can use {cmd_mention}. Click the Patreon button to get started!"),
            (
                "Already a patron?",
                f"[Check the troubleshooting page.]({troubleshoot_url})",
            ),
            title="Premium feature",
            help=docs_url("premium/character-images"),
        )

    async def _report_lockdown(self, ctx: AppInvocation, lockdown: datetime):
        """Tell the user when maintenance is scheduled."""
        timestamp = discord.utils.format_dt(lockdown, "R")
        err = f"{ctx.bot.me.mention} is undergoing maintenance {timestamp}."
        embed = ui.embeds.ErrorEmbed(
            ctx.user,
            err,
            title="Command temporarily unavailable",
            footer="Sorry for any inconvenience.",
        )
        await ctx.respond(embed=embed, ephemeral=True)

    async def _outage_alert(self, ctx: AppInvocation):
        """Warn the channel that a Discord issue is affecting the bot."""
        if not isinstance(ctx.channel, discord.abc.Messageable):
            return
        try:
            await ctx.channel.send(
                (
                    f"**Alert:** A Discord issue is currently impacting "
                    f"{self.bot.me.mention}'s responsiveness. Check status here: "
                    "https://discordstatus.com"
                ),
                delete_after=15,
            )
        except discord.HTTPException as err:
            logger.error("Couldn't post an outage alert: {}", str(err))

    async def _report_unknown(self, ctx: AppInvocation, error: BaseException):
        """Log an unknown error, notify the user, and post it to the report channel."""
        # Log first, so the error is recorded even if reporting fails
        formatted = "".join(traceback.format_exception(error))
        logger.error("{}: {}", error_scope(ctx), formatted)

        if isinstance(error, pymongo.errors.PyMongoError):
            try:
                await report_database_error(self.bot, ctx)
            except Exception as err:
                logger.error("Couldn't report a database error: {}", str(err))

        embed = await self.error_embed(ctx, error)
        user_msg = f"{self.bot.me.mention} has encountered an error. Support has been notified!"

        try:
            await ctx.respond(user_msg, ephemeral=True)
        except discord.HTTPException as err:
            logger.error("Couldn't inform user of an error: {}", str(err))
        finally:
            if self.channel is not None:
                try:
                    await self.channel.send(embed=embed)
                except discord.HTTPException as err:
                    logger.error("Couldn't post an error report: {}", str(err))

    async def error_embed(self, ctx: AppInvocation, error: BaseException) -> discord.Embed:
        """Create an error embed."""
        if isinstance(error, discord.HTTPException) and error.code == INVALID_WEBHOOK_TOKEN:
            description = "**Unrecoverable Discord error:** Invalid webhook token"
        else:
            description = "".join(traceback.format_exception(error))
            if len(description) > MAX_DESCRIPTION:
                # Keep the end, where the innermost frames and the error message are
                description = "…" + description[-(MAX_DESCRIPTION - 1) :]

        error_name = type(error).__name__

        embed = discord.Embed(
            title=f"{error_scope(ctx)}: {error_name}",
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

        embed.set_author(
            name=f"{ctx.user.name} ({ctx.user.id}) on {guild_name}", icon_url=guild_icon
        )

        return embed


reporter = ErrorReporter()
