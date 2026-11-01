"""interface/commandlistener.py - Log commands and follow them with tips, the MOTD, and the
changelog."""

import asyncio
from collections.abc import Awaitable, Callable
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

# Commands where the character option is needed even when the user has only
# one character
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
    """Runs after every command: logs it, then shows any tips, the MOTD, and the changelog."""

    def __init__(self, bot: InconnuBot):
        self.bot = bot
        self._changelog_pending: set[int] = set()

    @commands.Cog.listener()
    async def on_application_command(self, ctx: AppCtx):
        """Log the command, then show any follow-up messages in order. A failing
        step doesn't stop the rest."""
        if ctx.command is None:
            return
        command = ctx.command.qualified_name

        await self._run(self._log_command, ctx, command)
        await asyncio.sleep(1)  # Let the command's own response go first

        for step in (
            self._tip_unneeded_character_option,
            self._show_motd,
            self._show_changelog,
        ):
            await self._run(step, ctx, command)

    @staticmethod
    async def _run(step: Callable[[AppCtx, str], Awaitable[None]], ctx: AppCtx, command: str):
        """Run a step, logging rather than raising any failure."""
        try:
            await step(ctx, command)
        except Exception:
            logger.exception("{} failed after /{}", getattr(step, "__name__", step), command)

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
        try:
            await cmd_replace_respond(ctx, embed=self.bot.motd, ephemeral=True)
            self.bot.motd_given.add(ctx.user.id)
        except discord.HTTPException:
            logger.warning("Could not show MOTD to {}", ctx.user.name)

    async def _show_changelog(self, ctx: AppCtx, command: str):
        """Show the user the latest changelog the first time they run a command
        after an update. This is skipped if they're a new user."""
        if ctx.user.id in self._changelog_pending:
            # User triggered more than one command before we could finish
            # deciding whether to show the changelog. To avoid showing two,
            # we'll bail here and let the first task figure it out.
            return
        self._changelog_pending.add(ctx.user.id)

        try:
            vuser = await VUser.get_or_fetch(ctx.user.id)
            release_info = await changelog.fetch_changelog()
            # A release without notes still counts as seen
            has_notes = bool(release_info.text.strip())
            if has_notes and await self._should_see_changelog(
                ctx, command, vuser, release_info.tag
            ):
                note = (
                    f"-# {self.bot.me.mention} recently updated. You'll only "
                    "see this once; use `/changelog` to see it again."
                )
                view = changelog.build_changelog(self.bot, release_info, note=note)
                await ctx.respond(view=view, ephemeral=True)

            # Regardless of whether they're shown the changelog, we save the
            # last bot version used so they'll be shown the changelog next
            # update.
            vuser.last_version_used = release_info.tag
            if vuser.id is None or vuser.is_changed:
                await vuser.save()
        except (aiohttp.ClientError, KeyError) as err:
            logger.warning("Unable to fetch changelog: {!r}", err)
        finally:
            # If they were shown a changelog, it doesn't really matter if we
            # clear them from the queue; however, if we weren't able to fetch
            # the changelog, then clearing them allows us to try again in the
            # future.
            self._changelog_pending.discard(ctx.user.id)

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
        # whether their VUser was inserted. Instead, we have to query the
        # command_log to see if they ever ran a command before.
        if command == "changelog":
            # They don't need to be shown the changelog a second time.
            return False
        if vuser.last_version_used == current_version:
            # This only gets written by _show_changelog().
            return False

        # The versions don't match, but we need to see if they've ever run a
        # command to decide whether to show the changelog. If they haven't,
        # they're new and don't need to see it.
        prior_command = await db.command_log.find_one(
            {
                "user": ctx.user.id,
                # We always log the command before running this check, so we
                # have to look for commands before this one.
                "date": {"$lt": ctx.interaction.created_at},
            }
        )
        return prior_command is not None


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(CommandListener(bot))
