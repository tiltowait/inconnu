"""Edit location and temporary effects on a posted RP header."""

from typing import TYPE_CHECKING, Any

import discord
from loguru import logger

import db
from ctx import AppCtx, Channel
from utils.text import clean_text

if TYPE_CHECKING:
    from bot import InconnuBot

BLUSH_TEXT = ("Blushed", "Not Blushed")


async def edit_location(ctx: AppCtx, message: discord.Message):
    """Validate ownership and open the location edit modal for a posted header."""
    webhook = await _resolve_webhook(ctx.bot, ctx.channel, message)

    if webhook is None and message.author != ctx.bot.user:
        await ctx.respond("This message isn't an RP header!", ephemeral=True)
        return

    record = await db.headers.find_one({"message": message.id})
    if record is None:
        await ctx.respond("This message isn't an RP header!", ephemeral=True)
        return

    owner = record["character"]["user"]
    if ctx.user.id != owner:
        logger.debug("Unauthorized RP header update attempt by {}", ctx.user.name)
        await ctx.respond("This isn't your RP header!", ephemeral=True)
        return

    logger.debug("{} is updating an RP header", ctx.user.name)
    modal = LocationChangeModal(message, webhook, title="Edit RP Header")
    await ctx.send_modal(modal)


async def _resolve_webhook(
    bot: InconnuBot,
    channel: Channel,
    message: discord.Message,
) -> discord.Webhook | None:
    """Resolve a webhook if the message was sent by one of ours."""
    if not isinstance(channel, discord.TextChannel):
        return None
    try:
        return await bot.webhook_cache.fetch_webhook(channel, message.author.id)
    except discord.errors.Forbidden:
        logger.info("EDIT HEADER: No webhook permissions")
        return None


class LocationChangeModal(discord.ui.Modal):
    """A modal for changing RP header location."""

    def __init__(
        self, header: discord.Message, webhook: discord.Webhook | None, *args: Any, **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self.header = header
        self.webhook = webhook
        self.updating_title = webhook is None

        self.add_item(
            discord.ui.InputText(
                label="New Location",
                placeholder="The location where the scene takes place",
                value=self._get_location(),
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

    def _heading_elements(self) -> list[str]:
        """Split the heading. Some headers have a title; others use the author."""
        embed = self.header.embeds[0]
        heading = embed.title if self.updating_title else getattr(embed.author, "name", "")
        return [element for element in (heading or "").split(" • ") if element]

    def _get_location(self) -> str:
        """Get the header's current location."""
        elements = self._heading_elements()

        if not elements:
            return ""
        if len(elements) == 1:
            # Character name isn't given when the header is in the author
            # field. If we're looking at the embed title, then, no location
            # exists; otherwise, it's the only element, unless that's the Blush.
            if self.updating_title or elements[0] in BLUSH_TEXT:
                return ""
            return elements[0]
        if len(elements) == 2:
            if self.updating_title:
                if elements[-1] in BLUSH_TEXT:
                    return ""
                return elements[-1]

            return elements[0]

        # 3 elements; this could also be elements[1]
        return elements[-2]

    async def callback(self, interaction: discord.Interaction):
        """Update the RP header."""
        location = clean_text((self.children[0].value or "").replace("•", ""))
        temp_effects = clean_text(self.children[1].value or "")

        if not location:
            # Not responding keeps the modal open, with the player's input intact
            return

        embed = self.header.embeds[0]

        elements = self._heading_elements()

        if self._get_location():
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
            url = getattr(embed.author, "url", None)
            icon_url = getattr(embed.author, "icon_url", None)
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
