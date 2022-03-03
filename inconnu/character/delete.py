"""delete.py - Character deletion facilities."""

import discord

import inconnu
from ..views import DisablingView

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=character-deletion"


async def delete(ctx, character: str):
    """Prompt whether the user actually wants to delete the character."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild.id, ctx.user.id, character)

        if await inconnu.settings.accessible(ctx.user):
            msg_contents = __prompt_text(character)
        else:
            msg_contents = __prompt_embed(ctx, character)

        delete_view = _DeleteView(character)
        msg_contents["view"] = delete_view

        msg = await ctx.respond(**msg_contents)
        delete_view.message = msg

    except inconnu.vchar.errors.CharacterError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)


def __prompt_text(character):
    """Ask the user whether to delete the character, in plain text."""
    content = f"Really delete {character.name}? This will delete all associated data!\n"
    return { "content": content, "ephemeral": True }


def __prompt_embed(ctx, character):
    """Ask the user whether to delete the character, using an embed."""
    embed = discord.Embed(
        title=f"Delete {character.name}",
        color=0xFF0000
    )
    embed.set_author(name=ctx.user.display_name, icon_url=ctx.user.display_avatar)
    embed.add_field(name="Are you certain?", value="This will delete all associated data.")
    embed.set_footer(text="THIS ACTION CANNOT BE UNDONE")

    return { "embed": embed, "ephemeral": True }


class _DeleteView(DisablingView):
    """A view for deleting characters."""

    def __init__(self, character):
        super().__init__(timeout=20)
        self.character = character


    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, _, interaction):
        """Cancel the interaction."""
        await interaction.response.edit_message(
            content="Deletion canceled.",
            embed=None,
            view=None
        )
        self.stop()


    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete(self, _, interaction):
        """Delete the character."""
        await self.disable_items(interaction)

        if await inconnu.char_mgr.remove(self.character):
            msg = f"Deleted **{self.character.name}**!"
            ephemeral = False
        else:
            msg = "Something went wrong. Unable to delete."
            ephemeral = True

        await interaction.followup.send(msg, ephemeral=ephemeral)


    async def on_timeout(self):
        """Cancel out the message on timeout."""
        if self.message is not None:
            await self.message.edit_original_message(
                content=f"Canceled deletion of **{self.character.name}** due to time elapsed.",
                embed=None,
                view=None
            )
