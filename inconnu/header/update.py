"""inconnu/headers/update.py - Update RP headers."""

import asyncio

import discord

import inconnu
from logger import Logger

__HELP_URL = "https://docs.inconnu.app/command-reference/characters/rp-headers"


async def update_header(ctx: discord.ApplicationContext, character, blush: int):
    """Update the character's RP header."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild, ctx.user, character)
        modal = _RPHeader(character, blush, title=f"Update RP Header: {character.name}")
        await ctx.send_modal(modal)

    except inconnu.errors.CharacterNotFoundError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)


class _RPHeader(discord.ui.Modal):
    """A modal for setting character RP header details."""

    def __init__(self, character, blush, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.character = character
        self.blush = blush

        # Since the location field is the embed title, we have to ensure that
        # we don't exceed the maximum length of 256. We use the non-blush text
        # in case the status somehow changes mid-scene. For instance, a mortal
        # might be embraced, or a night might end at a haven, then resume the
        # next night pre-blush. By using the non-blush text, we ensure we don't
        # get any nasty surprises (though name changes mid-scene could still be
        # a problem, which is why we limit the title on show).
        mock_title = inconnu.header.header_title(character.name, "Not Blushed", "")
        max_location_len = 256 - len(mock_title)

        Logger.debug("HEADER: Header length, minus location, is %s", len(mock_title))
        Logger.debug("HEADER: Max location length: %s", max_location_len)

        self.add_item(
            discord.ui.InputText(
                label="Scene Location",
                placeholder="The location of the current scene",
                value=character.header.location,
                min_length=1,
                max_length=max_location_len,
            ),
        )
        self.add_item(
            discord.ui.InputText(
                label="Relevant Merits",
                placeholder="Merits characters would know or your scene partner SHOULD know.",
                value=character.header.merits,
                min_length=0,
                max_length=300,
                required=False,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Relevant Flaws",
                placeholder="Flaws characters would know or your scene partner SHOULD know.",
                value=character.header.flaws,
                min_length=0,
                max_length=300,
                required=False,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Temporary Effects",
                placeholder="Temporary effects currently affecting your character.",
                value=character.header.temp,
                max_length=512,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Set the header and tell the user."""
        self.character.header.location = inconnu.utils.clean_text(self.children[0].value)
        self.character.header.merits = inconnu.utils.clean_text(self.children[1].value)
        self.character.header.blush = self.blush
        self.character.header.flaws = inconnu.utils.clean_text(self.children[2].value)
        self.character.header.temp = inconnu.utils.clean_text(self.children[3].value)

        await asyncio.gather(
            interaction.response.send_message(
                f"Updated **{self.character.name}'s** RP header!", ephemeral=True
            ),
            self.character.commit(),
        )
