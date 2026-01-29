"""delete.py - Character deletion facilities."""

import asyncio

import discord
from discord.ui import InputText, Modal
from loguru import logger

import api
import errors
import inconnu

__HELP_URL = "https://docs.inconnu.app/command-reference/characters/deletion"


async def delete(ctx, character_name: str):
    """Prompt whether the user actually wants to delete the character."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild.id, ctx.user.id, character_name)
        modal = _DeletionModal(title=f"Delete {character.name}", character=character)
        await ctx.send_modal(modal)

    except errors.CharacterError as err:
        await inconnu.embeds.error(ctx, err, help_url=__HELP_URL)


class _DeletionModal(Modal):
    """A modal that requires the user to type the character's name before deleting."""

    def __init__(self, *args, **kwargs) -> None:
        self.character = kwargs.pop("character")
        super().__init__(*args, **kwargs)

        self.add_item(
            InputText(label="Enter character name to delete", placeholder=self.character.name)
        )

    async def callback(self, interaction: discord.Interaction):
        """Delete the character if its name was typed correctly."""
        if interaction.user is None:
            raise ValueError("Somehow don't have a user")

        user_input = self.children[0].value

        if user_input == self.character.name:
            msg = f"Deleted **{self.character.name}**!"

            await asyncio.gather(
                interaction.response.send_message(msg),
                inconnu.common.report_update(
                    ctx=interaction,
                    character=self.character,
                    title="Character Deleted",
                    message=f"**{interaction.user.mention}** deleted **{self.character.name}**.",
                ),
            )
            try:
                await api.delete_character_faceclaims(self.character)
            except api.ApiError as err:
                logger.error("Unable to delete {}: {}", self.character.name, err)

            await inconnu.char_mgr.remove(self.character)  # Has to be done after image deletion
        else:
            await inconnu.embeds.error(interaction, "You must type the character's name exactly.")
