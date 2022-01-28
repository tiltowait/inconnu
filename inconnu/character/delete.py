"""delete.py - Character deletion facilities."""

import discord

import inconnu
from ..views import DisablingView
from .. import common
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=character-deletion"


async def delete(ctx, character: str):
    """Prompt whether the user actually wants to delete the character."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.user.id, character)

        if inconnu.settings.accessible(ctx.user):
            await __prompt_text(ctx, character)
        else:
            await __prompt_embed(ctx, character)


    except errors.CharacterError as err:
        await common.present_error(ctx, err, help_url=__HELP_URL)


async def __prompt_text(ctx, character):
    """Ask the user whether to delete the character, in plain text."""
    contents = f"Really delete {character.name}? This will delete all associated data!\n"
    return await ctx.respond(contents, view=_DeleteView(character), ephemeral=True)


async def __prompt_embed(ctx, character):
    """Ask the user whether to delete the character, using an embed."""
    embed = discord.Embed(
        title=f"Delete {character.name}",
        color=0xFF0000
    )
    embed.set_author(name=ctx.user.display_name, icon_url=ctx.user.display_avatar)
    embed.add_field(name="Are you certain?", value="This will delete all associated data.")
    embed.set_footer(text="THIS ACTION CANNOT BE UNDONE")

    return await ctx.respond(embed=embed, view=_DeleteView(character), ephemeral=True)


class _DeleteView(DisablingView):
    """A view for deleting characters."""

    def __init__(self, character):
        super().__init__(self)
        self.character = character


    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction):
        """Cancel the interaction."""
        await interaction.response.send_message("Deletion canceled.", ephemeral=True)
        await self.disable_items(interaction)


    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction):
        """Delete the character."""
        if self.character.delete_character():
            await interaction.response.send_message(f"Deleted **{self.character.name}**!")
        else:
            await interaction.response.send_message("Something went wrong. Unable to delete.", ephemeral=True)

        await self.disable_items(interaction)
