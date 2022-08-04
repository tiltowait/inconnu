"""Header commands."""
# pylint: disable=no-self-use

import discord
from discord.commands import Option, OptionChoice, SlashCommandGroup, slash_command
from discord.ext import commands
from pymongo import DeleteOne

import inconnu
from logger import Logger


class LocationChangeModal(discord.ui.Modal):
    """A modal for changing RP header location."""

    def __init__(self, header: discord.Message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header = header

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
                max_length=100,
                required=False,
            )
        )

    def get_location(self):
        """Get the header's current location."""
        elements = self.header.embeds[0].title.split(" • ")
        if len(elements) > 1 and "Blushed" not in elements[-1]:
            return elements[-1]
        return ""

    async def callback(self, interaction: discord.Interaction):
        """Update the RP header."""
        location = " ".join(self.children[0].value.split())
        temp_effects = " ".join(self.children[1].value.split())
        embed = self.header.embeds[0]

        # The title contains name, blush, location, but only name is guaranteed
        elements = embed.title.split(" • ")
        if len(elements) > 1 and "Blushed" not in elements[-1]:
            # We do have location info
            elements.pop()

        # Add the location
        elements.append(location)
        embed.title = " • ".join(elements)
        embed.set_footer(text=temp_effects)

        await self.header.edit(embed=embed)

        # Inform the user
        temp_effects = temp_effects or "*None*"
        embed = discord.Embed(
            title="Header Updated",
            description=f"**Location:** {location}\n**Temporary Effects:** {temp_effects}",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def _header_bol_options(ctx):
    """Generate options for the BoL portion of the header update command."""
    if (charid := ctx.options.get("character")) is None:
        return []

    guild = ctx.interaction.guild
    user = ctx.interaction.user

    try:
        character = await inconnu.char_mgr.fetchone(guild, user, charid)

        if character.is_thin_blood:
            return [OptionChoice("N/A - Thin-Blood", -1)]
        if character.is_vampire:
            return [
                OptionChoice("Yes", 1),
                OptionChoice("No", 0),
                OptionChoice("N/A - Thin-Blood", -1),
            ]
        return [OptionChoice("N/A - Mortal", -1)]

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
        location: Option(str, "THIS POST ONLY: Where the scene is taking place", required=False),
        merits: Option(str, "THIS POST ONLY: Obvious/important merits", required=False),
        flaws: Option(str, "THIS POST ONLY: Obvious/important flaws", required=False),
        temporary: Option(str, "THIS POST ONLY: Temporary affects", required=False),
    ):
        """Display your character's RP header."""
        await inconnu.header.show_header(
            ctx,
            character,
            blush=blush,
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
            int, "Is Blush of Life active?", autocomplete=_header_bol_options, required=True
        ),
    ):
        """Update your character's RP header."""
        await inconnu.header.update_header(ctx, character, blush)

    @commands.message_command(name="Fix RP Header")
    @commands.guild_only()
    async def fix_rp_header(self, ctx, message: discord.Message):
        """Change an RP header's location."""
        if message.author == self.bot.user:
            # Make sure we have a header
            record = await inconnu.db.headers.find_one({"message": message.id})
            if record is not None:
                # Make sure we are allowed to update it
                owner = record["character"]["user"]
                if ctx.channel.permissions_for(ctx.user).administrator or owner == ctx.user.id:
                    # Modal gets the new location
                    Logger.debug(
                        "HEADER: %s#%s is updating an RP header",
                        ctx.user.name,
                        ctx.user.discriminator,
                    )
                    modal = LocationChangeModal(message, title="Fix RP Header Location")
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

    @commands.message_command(name="Delete RP Header")
    @commands.guild_only()
    async def delete_rp_header(self, ctx, message: discord.Message):
        """Delete an RP header."""
        if message.author == self.bot.user:
            record = await inconnu.db.headers.find_one({"message": message.id})
            if record is not None:
                # Make sure we are allowed to delete it
                owner = record["character"]["user"]
                if ctx.channel.permissions_for(ctx.user).administrator or owner == ctx.user.id:
                    Logger.debug("HEADER: Deleting RP header")
                    await message.delete()
                    await ctx.respond("RP header deleted!", ephemeral=True)
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
        raw_ids = payload.message_ids
        deletions = []

        for message in payload.cached_messages:
            raw_ids.discard(message.id)
            if message.author == self.bot.user:
                Logger.debug("HEADER: Adding potential header message to deletion queue")
                deletions.append(DeleteOne({"message": message.id}))

        for message_id in raw_ids:
            Logger.debug("HEADER: Blindly adding potential header message to deletion queue")
            deletions.append(DeleteOne({"message": message_id}))

        Logger.debug("HEADER: Deleting %s potential header messages", len(deletions))
        await inconnu.db.headers.bulk_write(deletions)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, raw_message):
        """Remove a header record."""
        # We only have a raw message event, which may not be in the message
        # cache. If it isn't, then we just have to blindly attempt to remove
        # the record. If this proves to be a performance hit, we'll have to
        # revert to using on_message_delete().
        if (message := raw_message.cached_message) is not None:
            # Got a cached message, so we can be a little more efficient and
            # only call the database if it belongs to the bot
            if message.author == self.bot.user:
                Logger.debug("HEADER: Deleting possible header message")
                await inconnu.db.headers.delete_one({"message": message.id})
        else:
            # The message isn't in the cache; blindly delete the record
            # if it exists
            Logger.debug("HEADER: Blindly deleting potential header record")
            await inconnu.db.headers.delete_one({"message": raw_message.message_id})


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(HeaderCog(bot))
