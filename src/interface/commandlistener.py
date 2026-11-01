"""interface/commandlistener.py - Log commands and follow them with tips and the MOTD."""

import asyncio
from typing import TYPE_CHECKING, cast

import aiohttp
import discord
from discord.ext import commands
from loguru import logger

import db
import errors
import services
from ctx import AppCtx
from inconnu.misc import changelog
from models import VUser
from utils import cmd_replace_respond, command_options, raw_command_options

if TYPE_CHECKING:
    from bot import InconnuBot

# Commands where the character option is needed even when the user has only one character
CHARACTER_OPTION_REQUIRED = frozenset(
    {
        "character bio edit",
        "character delete",
        "experience remove entry",
        "experience award",
        "experience deduct",
        "update header",
        "transfer",
    }
)
# Commands that shouldn't show the MOTD
MOTD_EXEMPT = frozenset({"motd", "announce"})


class CommandListener(commands.Cog):
    """Runs after every command: logs it, then shows any tips and the MOTD."""

    def __init__(self, bot: InconnuBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_application_command(self, ctx: AppCtx):
        """Run each post-command step in order. A failing step doesn't stop the rest."""
        if ctx.command is None:
            return

        steps = (
            self._log_command,
            self._tip_unneeded_character_option,
            self._show_motd,
            self._show_changelog,
        )
        for step in steps:
            try:
                await step(ctx, ctx.command.qualified_name)
            except Exception:
                logger.exception("{} failed after /{}", step.__name__, ctx.command.qualified_name)

    async def _log_command(self, ctx: AppCtx, command: str):
        """Log command usage."""
        location = ctx.guild.name if ctx.guild is not None else "DMs"
        logger.info(
            "`/{}` invoked by {} ({}) in {} ({}). Options: {}",
            command,
            ctx.user.name,
            ctx.user.id,
            location,
            ctx.guild_id,
            command_options(ctx.interaction),
        )

        await db.command_log.insert_one(
            {
                "guild": ctx.guild_id,
                "user": ctx.user.id,
                "locale": ctx.interaction.locale,
                "command": command,
                "type": getattr(ctx.command, "type", None),
                "options": [
                    {"name": name, "value": value}
                    for name, value in raw_command_options(ctx.interaction).items()
                ],
                "date": ctx.interaction.created_at,
            }
        )

    async def _tip_unneeded_character_option(self, ctx: AppCtx, command: str):
        """Tell a user with one character they don't need the character option."""
        options = raw_command_options(ctx.interaction)
        if "character" not in options or "player" in options:
            return
        if ctx.guild is None or command in CHARACTER_OPTION_REQUIRED:
            return

        member = cast(discord.Member, ctx.user)
        if await services.char_mgr.character_count(ctx.guild, member) != 1:
            return

        # They may have used an SPC, which doesn't count toward their characters
        try:
            character = await services.char_mgr.fetchone(ctx.guild, member, options["character"])
        except errors.CharacterNotFoundError:
            return
        if not character.is_pc:
            return

        await asyncio.sleep(1)  # Make sure it shows after the command
        tip = (
            "**Tip:** You only have one character, so you don't need "
            f"the `character` option for `/{command}`."
        )
        await cmd_replace_respond(ctx, tip, ephemeral=True)

    async def _show_motd(self, ctx: AppCtx, command: str):
        """Show the MOTD once per user."""
        if self.bot.motd is None or command in MOTD_EXEMPT:
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

    async def _show_changelog(self, ctx: AppCtx, command: str):
        """Show the user the latest changelog the first time they run a command
        after an update. This is skipped if they're a new user."""
        vuser = await VUser.get_or_fetch(ctx.user.id)
        try:
            release_info = await changelog.fetch_changelog()
            if await self._should_see_changelog(ctx, command, vuser, release_info.tag):
                await ctx.respond(view=changelog.build_changelog(release_info), ephemeral=True)

            # Regardless of whether they're shown the changelog, we set the
            # last bot version used and save it so they'll be shown the
            # changelog next update.
            vuser.last_version_used = release_info.tag
            if vuser.id is None or vuser.is_changed:
                await vuser.save()
        except aiohttp.ClientError, KeyError:
            logger.warning("Unable to fetch changelog")

    @staticmethod
    async def _should_see_changelog(
        ctx: AppCtx, command: str, vuser: VUser, current_version: str
    ) -> bool:
        """Checks if the user should see the changelog."""
        # Prior to the creation of the auto-changelog functionality, VUser was
        # only written if the user changed the default settings. Consequently,
        # only 2.7% of users had a VUser document.
        #
        # New users shouldn't see the changelog, but we can't just rely on
        # VUser.is_inserted. Instead, we have to query the command_log to see
        # if they ever ran a command before.
        if command == "changelog":
            return False
        if vuser.last_version_used == current_version:
            # This only gets written by _show_changelog().
            return False

        # If they ever used the bot before the command that triggered this
        # check, then they are not a new user. If their first command was this
        # one, then they are new and don't need to see the changelog.
        prior_command = await db.command_log.find_one(
            {
                "user": ctx.user.id,
                "date": {"$lt": ctx.interaction.created_at},
            }
        )
        return prior_command is not None


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(CommandListener(bot))
