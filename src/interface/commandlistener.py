"""interface/commandlistener.py - Log commands and follow them with tips and the MOTD."""

import asyncio
from typing import TYPE_CHECKING, cast

import discord
from discord.ext import commands
from loguru import logger

import db
import errors
import services
from ctx import AppCtx
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

        steps = (self._log_command, self._tip_unneeded_character_option, self._show_motd)
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


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(CommandListener(bot))
