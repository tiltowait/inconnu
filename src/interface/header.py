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
import interface
import services
from ctx import AppCtx
from inconnu.options import char_option
from utils.permissions import is_approved_user

if TYPE_CHECKING:
    from bot import InconnuBot


class LocationChangeModal(discord.ui.Modal):
    """A modal for changing RP header location."""

    def __init__(self, header: discord.Message, webhook: discord.Webhook | None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header = header
        self.webhook = webhook
        self.updating_title = webhook is None

        self.add_item(
            discord.ui.InputText(
                label="New Location",
                placeholder="The location where the scene takes place",
                value=self.get_location(),
                max_length=100,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Temporary Effects",
                placeholder="Temporary effects relevant to the scene",
                value=getattr(header.embeds[0].footer, "text", ""),
                max_length=512,
                required=False,
            )
        )

    def get_location(self):
        """Get the header's current location."""
        if self.updating_title:
            elements = self.header.embeds[0].title.split(" • ")
        else:
            elements = self.header.embeds[0].author.name.split(" • ")

        if len(elements) == 1:
            # Character name isn't given when the header is in the author
            # field. If we're looking at the embed title, then, no location
            # exists; otherwise, it's the first and only element.
            return "" if self.updating_title else elements[0]
        if len(elements) == 2:
            if self.updating_title:
                if "Blushed" in elements[-1]:
                    return ""
                return elements[-1]

            return elements[0]

        # 3 elements; this could also be elements[1]
        return elements[-2]

    async def callback(self, interaction: discord.Interaction):
        """Update the RP header."""
        location = " ".join(self.children[0].value.split())
        temp_effects = " ".join(self.children[1].value.split())
        embed = self.header.embeds[0]

        # Some headers have a title; others use the author string
        if self.updating_title:
            # The title contains name, blush, location, but only name is guaranteed
            logger.debug("EDIT HEADER: Embed has a title")
            elements = embed.title.split(" • ")
        else:
            logger.debug("EDIT HEADER: Embed does not have a title")
            elements = embed.author.name.split(" • ")

        if self.get_location():
            # We need to remove the old location
            if self.updating_title:
                del elements[1]
            else:
                del elements[0]

        # Generate the new heading
        insertion_index = 1 if self.updating_title else 0
        elements.insert(insertion_index, location)
        new_heading = " • ".join(elements)

        if self.updating_title:
            embed.title = new_heading
        else:
            url = embed.author.url
            icon_url = embed.author.icon_url
            embed.set_author(name=new_heading, url=url, icon_url=icon_url)

        embed.set_footer(text=temp_effects)

        if self.webhook is None:
            logger.debug("EDIT HEADER: Updating with Message.edit()")
            await self.header.edit(embed=embed)
        else:
            logger.debug("EDIT HEADER: Updating with Webhook.edit_message()")
            await self.webhook.edit_message(self.header.id, embed=embed)

        # Inform the user
        temp_effects = temp_effects or "*None*"
        embed = discord.Embed(
            title="Header Updated",
            description=f"**Location:** {location}\n**Temporary Effects:** {temp_effects}",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=5)


async def _header_bol_options(ctx) -> list[OptionChoice]:
    """Generate options for the BoL portion of the header update command."""
    if (charid := ctx.options.get("character")) is None:
        return []

    guild = ctx.interaction.guild
    user = ctx.interaction.user

    try:
        character = await services.char_mgr.fetchone(guild, user, charid)

        if character.is_thin_blood:
            return [OptionChoice("N/A - Thin-Blood", "-1")]
        if character.is_vampire:
            return [
                OptionChoice("Yes", "1"),
                OptionChoice("No", "0"),
                OptionChoice("N/A - Thin-Blood", "-1"),
            ]
        return [OptionChoice("N/A - Mortal", "-1")]

    except errors.CharacterNotFoundError:
        return []


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
    async def fix_rp_header(self, ctx, message: discord.Message):
        """Change an RP header's location."""
        possible_header = False
        webhook: discord.Webhook | None = None

        if message.author == self.bot.user:
            possible_header = True
        else:
            try:
                webhook = await self.bot.webhook_cache.fetch_webhook(ctx.channel, message.author.id)
                if webhook is not None:
                    logger.info("EDIT HEADER: Editing a WebhookMessage")
                    possible_header = True
                else:
                    logger.debug("EDIT HEADER: Not a WebhookMessage")
            except discord.errors.Forbidden:
                logger.info("EDIT HEADER: No webhook permissions")

        if possible_header:
            # Make sure we have a header
            record = await db.headers.find_one({"message": message.id})
            if record is not None:
                # Make sure we are allowed to update it
                owner = record["character"]["user"]
                if ctx.user.id == owner:
                    # Modal gets the new location
                    logger.debug("HEADER: {} is updating an RP header", ctx.user.name)
                    modal = LocationChangeModal(message, webhook, title="Edit RP Header")
                    await ctx.send_modal(modal)
                else:
                    logger.debug(
                        "HEADER: Unauthorized RP header update attempt by {}", ctx.user.name
                    )
                    await ctx.respond("This isn't your RP header!", ephemeral=True)
                return

        logger.debug("HEADER: {} attempted to update a non-header post", ctx.user.name)
        await ctx.respond("This message isn't an RP header!", ephemeral=True)

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
                if is_approved_user(ctx, owner_id=owner):
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
    async def on_raw_bulk_message_delete(self, payload):
        """Bulk delete headers."""
        deletions = interface.raw_bulk_delete_handler(
            payload,
            self.bot,
            lambda id: DeleteOne({"message": id}),
            author_comparator=lambda author: author.id in self.bot.webhook_cache.webhook_ids,
        )
        if deletions:
            logger.debug("HEADER: Deleting {} potential header messages", len(deletions))
            await db.headers.bulk_write(deletions)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, raw_message):
        """Remove a header record."""

        async def deletion_handler(message_id: int):
            """Delete the header record."""
            logger.debug("HEADER: Deleting possible header")
            await db.headers.delete_one({"message": message_id})

        await interface.raw_message_delete_handler(
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


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(HeaderCog(bot))
