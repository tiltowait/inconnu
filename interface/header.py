"""Header commands."""
# pylint: disable=no-self-use

import discord
from discord.commands import Option, OptionChoice, SlashCommandGroup, slash_command
from discord.ext import commands
from pymongo import DeleteOne

import inconnu
import interface
from logger import Logger


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
                value=header.embeds[0].footer.text,
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
            Logger.debug("EDIT HEADER: Embed has a title")
            elements = embed.title.split(" • ")
        else:
            Logger.debug("EDIT HEADER: Embed does not have a title")
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
            Logger.debug("EDIT HEADER: Updating with Message.edit()")
            await self.header.edit(embed=embed)
        else:
            Logger.debug("EDIT HEADER: Updating with Webhook.edit_message()")
            await self.webhook.edit_message(self.header.id, embed=embed)

        # Inform the user
        temp_effects = temp_effects or "*None*"
        embed = discord.Embed(
            title="Header Updated",
            description=f"**Location:** {location}\n**Temporary Effects:** {temp_effects}",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=5)


async def _header_bol_options(ctx) -> str:
    """Generate options for the BoL portion of the header update command."""
    if (charid := ctx.options.get("character")) is None:
        return []

    guild = ctx.interaction.guild
    user = ctx.interaction.user

    try:
        character = await inconnu.char_mgr.fetchone(guild, user, charid)

        if character.is_thin_blood:
            return [OptionChoice("N/A - Thin-Blood", "-1")]
        if character.is_vampire:
            return [
                OptionChoice("Yes", "1"),
                OptionChoice("No", "0"),
                OptionChoice("N/A - Thin-Blood", "-1"),
            ]
        return [OptionChoice("N/A - Mortal", "-1")]

    except inconnu.errors.CharacterNotFoundError:
        return []


class HeaderCog(commands.Cog):
    """A cog with header-related commands, including context menu commands."""

    def __init__(self, bot):
        self.bot = bot

    @slash_command()
    async def header(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character whose header to post"),
        blush: Option(
            int,
            "THIS POST ONLY: Is Blush of Life active?",
            choices=[OptionChoice("Yes", 1), OptionChoice("No", 0), OptionChoice("N/A", -1)],
            required=False,
        ),
        hunger: Option(
            int,
            "THIS POST ONLY: The character's Hunger (vampires only)",
            choices=[i for i in range(6)],
            required=False,
        ),
        location: Option(str, "THIS POST ONLY: Where the scene is taking place", required=False),
        merits: Option(str, "THIS POST ONLY: Obvious/important merits", required=False),
        flaws: Option(str, "THIS POST ONLY: Obvious/important flaws", required=False),
        temporary: Option(str, "THIS POST ONLY: Temporary effects", required=False),
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

    header_update = SlashCommandGroup("update", "Update commands")

    @header_update.command(name="header")
    async def update_header(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character whose header to update", required=True),
        blush: Option(
            str, "Is Blush of Life active?", autocomplete=_header_bol_options, required=True
        ),
    ):
        """Update your character's RP header."""
        # If the user selects a Blush option, then leaves channels, then comes
        # back and hits enter, Discord will send "Yes" instead of "1" (as an
        # example). Therefore, we need to check their response.
        try:
            blush = int(blush)
        except ValueError:
            blush = blush.lower()
            blush_options = {"yes": 1, "no": 0, "n/a - thin-blood": -1}
            if (blush := blush_options.get(blush)) is None:
                await inconnu.utils.error(ctx, f"Unknown Blush of Life option: `{blush}`.")
                return

        await inconnu.header.update_header(ctx, character, int(blush))

    @commands.message_command(name="Header: Edit")
    @commands.guild_only()
    async def fix_rp_header(self, ctx, message: discord.Message):
        """Change an RP header's location."""
        proceed = False
        if message.author == self.bot.user:
            webhook = None
            proceed = True
        else:
            try:
                webhook = await self.bot.webhook_cache.fetch_webhook(ctx.channel, message.author.id)
                if webhook is not None:
                    Logger.info("EDIT HEADER: Editing a WebhookMessage")
                    proceed = True
                else:
                    Logger.debug("EDIT HEADER: Not a WebhookMessage")
            except discord.errors.Forbidden:
                Logger.info("EDIT HEADER: No webhook permissions")

        if proceed:
            # Make sure we have a header
            record = await inconnu.db.headers.find_one({"message": message.id})
            if record is not None:
                # Make sure we are allowed to update it
                owner = record["character"]["user"]
                if ctx.user.id == owner:
                    # Modal gets the new location
                    Logger.debug(
                        "HEADER: %s#%s is updating an RP header",
                        ctx.user.name,
                        ctx.user.discriminator,
                    )
                    modal = LocationChangeModal(message, webhook, title="Edit RP Header")
                    await ctx.send_modal(modal)
                else:
                    Logger.debug(
                        "HEADER: Unauthorized RP header update attempt by %s#%s",
                        ctx.user.name,
                        ctx.user.discriminator,
                    )
                    await ctx.respond("This isn't your RP header!", ephemeral=True)
                return

        Logger.debug(
            "HEADER: %s#%s attempted to update a non-header post",
            ctx.user.name,
            ctx.user.discriminator,
        )
        await ctx.respond("This message isn't an RP header!", ephemeral=True)

    @commands.message_command(name="Header: Delete")
    @commands.guild_only()
    async def delete_rp_header(self, ctx, message: discord.Message):
        """Delete an RP header."""
        if message.author == self.bot.user:
            record = await inconnu.db.headers.find_one({"message": message.id})
            if record is not None:
                # Make sure we are allowed to delete it
                owner = record["character"]["user"]
                if inconnu.utils.is_admin(ctx, owner_id=owner):
                    Logger.debug("HEADER: Deleting RP header")
                    try:
                        await message.delete()
                        await ctx.respond("RP header deleted!", ephemeral=True, delete_after=3)
                    except discord.errors.Forbidden:
                        await ctx.respond(
                            (
                                "Something went wrong. Unable to delete the header. "
                                "This may be a permissions issue."
                            ),
                            ephemeral=True,
                        )
                        Logger.warning(
                            "HEADER: Unable to delete %s in #%s on %s",
                            record["message"],
                            ctx.channel.name,
                            ctx.guild.name,
                        )
                else:
                    Logger.debug(
                        "HEADER: Unauthorized deletion attempt by %s#%s",
                        ctx.user.name,
                        ctx.user.discriminator,
                    )
                    await ctx.respond(
                        "You don't have permission to delete this RP header.", ephemeral=True
                    )
            else:
                Logger.debug("HEADER: Attempted to delete non-header post")
                await ctx.respond("This is not an RP header.", ephemeral=True)
        else:
            Logger.debug("HEADER: Attempted to delete non-%s post", self.bot.user.name)
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
            Logger.debug("HEADER: Deleting %s potential header messages", len(deletions))
            await inconnu.db.headers.bulk_write(deletions)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, raw_message):
        """Remove a header record."""

        async def deletion_handler(message_id: int):
            """Delete the header record."""
            Logger.debug("HEADER: Deleting possible header")
            await inconnu.db.headers.delete_one({"message": message_id})

        await interface.raw_message_delete_handler(
            raw_message,
            self.bot,
            deletion_handler,
            author_comparator=lambda author: author.id in self.bot.webhook_cache.webhook_ids,
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Remove header records from the deleted channel."""
        Logger.info("HEADER: Removing header records from deleted channel %s", channel.name)
        await inconnu.db.headers.delete_many({"channel": channel.id})


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(HeaderCog(bot))
