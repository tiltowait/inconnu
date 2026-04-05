"""Edit location and temporary effects on a posted RP header."""

from typing import TYPE_CHECKING

import discord
from loguru import logger

import db
from ctx import AppCtx, Channel

if TYPE_CHECKING:
    from bot import InconnuBot


async def fix_header_location(ctx: AppCtx, message: discord.Message):
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
        logger.debug("HEADER: Unauthorized RP header update attempt by {}", ctx.user.name)
        await ctx.respond("This isn't your RP header!", ephemeral=True)
        return

    logger.debug("HEADER: {} is updating an RP header", ctx.user.name)
    modal = LocationChangeModal(message, webhook, title="Edit RP Header")
    await ctx.send_modal(modal)


async def _resolve_webhook(
    bot: "InconnuBot",
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

    def __init__(self, header: discord.Message, webhook: discord.Webhook | None, *args, **kwargs):
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

    def _get_location(self):
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
            logger.debug("EDIT HEADER: Embed has a title")
            elements = embed.title.split(" • ")
        else:
            logger.debug("EDIT HEADER: Embed does not have a title")
            elements = embed.author.name.split(" • ")

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
