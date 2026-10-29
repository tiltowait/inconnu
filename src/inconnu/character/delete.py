"""delete.py - Character deletion facilities."""

import asyncio
from typing import Any, cast

import discord
from discord.ui import InputText, Modal
from loguru import logger

import api
import errors
import services
import ui
from ctx import AppCtx, AppInteraction
from models import VChar
from utils.urls import docs_url

__HELP_URL = docs_url("command-reference/characters#character-delete")


async def delete(ctx: AppCtx, character_name: str):
    """Prompt whether the user actually wants to delete the character."""
    if ctx.guild is None:
        await ui.embeds.error(ctx, "This command is unavailable in DMs.")
        return

    try:
        character = await services.char_mgr.fetchone(
            ctx.guild, cast(discord.Member, ctx.user), character_name
        )
        modal = _DeletionModal(title=f"Delete {character.name}", character=character)
        await ctx.send_modal(modal)

    except errors.CharacterError as err:
        await ui.embeds.error(ctx, err, help=__HELP_URL)


class _DeletionModal(Modal):
    """A modal that requires the user to type the character's name before deleting."""

    def __init__(self, *args: Any, **kwargs: Any):
        self.character: VChar = kwargs.pop("character")
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
                services.post_update(
                    ctx=cast(AppInteraction, interaction),
                    character=self.character,
                    title="Character Deleted",
                    message=f"**{interaction.user.mention}** deleted **{self.character.name}**.",
                ),
            )
            try:
                await api.delete_character_faceclaims(self.character)
            except api.ApiError as err:
                logger.error("Unable to delete {}: {}", self.character.name, err)

            await services.char_mgr.remove(self.character)  # Has to be done after image deletion
        else:
            await ui.embeds.error(interaction, "You must type the character's name exactly.")
