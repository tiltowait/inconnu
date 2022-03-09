"""delete.py - Character deletion facilities."""

import asyncio

import discord
from discord.ui import InputText, Modal

import inconnu

__HELP_URL = "https://www.inconnu-bot.com/#/character-tracking?id=character-deletion"


async def delete(ctx, character: str):
    """Prompt whether the user actually wants to delete the character."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild.id, ctx.user.id, character)
        modal = _DeletionModal(title=f"Delete {character.name}", character=character)
        await ctx.send_modal(modal)

    except inconnu.vchar.errors.CharacterError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)


class _DeletionModal(Modal):
    """A modal that requires the user to type the character's name before deleting."""

    def __init__(self, *args, **kwargs) -> None:
        self.character = kwargs.pop("character")
        super().__init__(*args, **kwargs)

        self.add_item(
            InputText(
                label="Enter character name to delete",
                placeholder=self.character.name
            )
        )


    async def callback(self, interaction: discord.Interaction):
        """Delete the character if its name was typed correctly."""
        user_input = self.children[0].value

        if user_input == self.character.name:
            tasks = []

            msg = f"Deleted **{self.character.name}**!"
            tasks.append(inconnu.char_mgr.remove(self.character))
            tasks.append(interaction.response.send_message(msg))

            tasks.append(inconnu.common.report_update(
                ctx=interaction,
                character=self.character,
                title="Character Deleted",
                message=f"**{interaction.user.mention}** deleted **{self.character.name}**."
            ))

            await asyncio.gather(*tasks)
        else:
            await inconnu.common.present_error(
                interaction, "You must type the character's name exactly."
            )
