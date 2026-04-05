"""Header commands."""

from typing import TYPE_CHECKING

import discord
from discord import option
from discord.commands import OptionChoice, SlashCommandGroup, slash_command
from discord.ext import commands
from loguru import logger
from pymongo import DeleteOne

import db
import errors
import inconnu
from ctx import AppCtx
from inconnu.options import char_option
from utils.discord_helpers import raw_bulk_delete_handler, raw_message_delete_handler
from utils.permissions import is_approved_user

if TYPE_CHECKING:
    from bot import InconnuBot


class HeaderCog(commands.Cog):
    """A cog with header-related commands, including context menu commands."""

    def __init__(self, bot: "InconnuBot"):
        self.bot = bot

    @slash_command(contexts={discord.InteractionContextType.guild})
    @char_option("The character whose header to post")
    @option(
        "blush",
        description="THIS POST ONLY: Is Blush of Life active?",
        choices=[OptionChoice("Yes", 1), OptionChoice("No", 0), OptionChoice("N/A", -1)],
        required=False,
    )
    @option(
        "hunger",
        description="THIS POST ONLY: The character's Hunger (vampires only)",
        choices=[i for i in range(6)],
        required=False,
    )
    @option(
        "location", description="THIS POST ONLY: Where the scene is taking place", required=False
    )
    @option("merits", description="THIS POST ONLY: Obvious/important merits", required=False)
    @option("flaws", description="THIS POST ONLY: Obvious/important flaws", required=False)
    @option("temporary", description="THIS POST ONLY: Temporary effects", required=False)
    async def header(
        self,
        ctx: AppCtx,
        character: str,
        blush: int,
        hunger: int,
        location: str,
        merits: str,
        flaws: str,
        temporary: str,
    ):
        """Display your character's RP header."""
        await inconnu.header.show_header(
            ctx,
            character,
            blush=blush,
            hunger=hunger,
            location=location,
            merits=merits,
            flaws=flaws,
            temp=temporary,
        )

    header_update = SlashCommandGroup(
        "update",
        "Update commands",
        contexts={discord.InteractionContextType.guild},
    )

    @header_update.command(name="header")
    @char_option("The character whose header to update")
    async def update_header(
        self,
        ctx: AppCtx,
        character: str,
    ):
        """Update your character's RP header."""
        await inconnu.header.update_header(ctx, character)

    @commands.message_command(name="Header: Edit", contexts={discord.InteractionContextType.guild})
    async def fix_rp_header(self, ctx: AppCtx, message: discord.Message):
        """Change an RP header's location."""
        await inconnu.header.fix.fix_header_location(ctx, message)

    @commands.message_command(
        name="Header: Delete",
        contexts={discord.InteractionContextType.guild},
    )
    async def delete_rp_header(self, ctx: AppCtx, message: discord.Message):
        """Delete an RP header."""
        try:
            webhook = await self.bot.prep_webhook(message.channel)
            is_bot_message = message.author == self.bot.user
            is_webhook_message = message.author.id == webhook.id
        except errors.WebhookError:
            webhook = None
            is_bot_message = message.author == self.bot.user
            is_webhook_message = False

        if is_bot_message or is_webhook_message:
            record = await db.headers.find_one({"message": message.id})
            if record is not None:
                # Make sure we are allowed to delete it
                owner = record["character"]["user"]
                if is_approved_user(ctx, owner=owner):
                    logger.debug("HEADER: Deleting RP header")
                    try:
                        if is_bot_message:
                            logger.debug("HEADER: Calling message.delete()")
                            await message.delete()
                        else:
                            logger.debug("HEADER: Calling webhook.delete_message()")
                            await webhook.delete_message(message.id)
                        await ctx.respond("RP header deleted!", ephemeral=True, delete_after=3)
                    except discord.errors.Forbidden:
                        await ctx.respond(
                            (
                                "Something went wrong. Unable to delete the header. "
                                "This may be a permissions issue."
                            ),
                            ephemeral=True,
                        )
                        logger.warning(
                            "HEADER: Unable to delete {} in #{} on {}",
                            record["message"],
                            ctx.channel.name,
                            ctx.guild.name,
                        )
                else:
                    logger.debug("HEADER: Unauthorized deletion attempt by {}", ctx.user.name)
                    await ctx.respond(
                        "You don't have permission to delete this RP header.", ephemeral=True
                    )
            else:
                logger.debug("HEADER: Attempted to delete non-header post")
                await ctx.respond("This is not an RP header.", ephemeral=True)
        else:
            logger.debug("HEADER: Attempted to delete someone else's post")
            await ctx.respond("This is not an RP header.", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        """Bulk delete headers."""
        deletions = raw_bulk_delete_handler(
            payload,
            self.bot,
            lambda id: DeleteOne({"message": id}),
            author_comparator=lambda author: author.id in self.bot.webhook_cache.webhook_ids,
        )
        if deletions:
            logger.debug("HEADER: Deleting {} potential header messages", len(deletions))
            await db.headers.bulk_write(deletions)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, raw_message: discord.RawMessageDeleteEvent):
        """Remove a header record."""

        async def deletion_handler(message_id: int):
            """Delete the header record."""
            logger.debug("HEADER: Deleting possible header")
            await db.headers.delete_one({"message": message_id})

        await raw_message_delete_handler(
            raw_message,
            self.bot,
            deletion_handler,
            author_comparator=lambda author: author.id in self.bot.webhook_cache.webhook_ids,
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Remove header records from the deleted channel."""
        logger.info("HEADER: Removing header records from deleted channel {}", channel.name)
        await db.headers.delete_many({"channel": channel.id})


def setup(bot: "InconnuBot"):
    """Add the cog to the bot."""
    bot.add_cog(HeaderCog(bot))
