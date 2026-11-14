"""inconnu/headers/update.py - Update RP headers."""

import asyncio
from typing import Any, cast

import discord
from loguru import logger

import inconnu
from ctx import AppCtx
from models import BlushState, VChar
from models.rpheader import NOT_BLUSHED
from services.haven import haven
from utils.text import clean_text
from utils.urls import docs_url

__HELP_URL = docs_url("command-reference/characters#rp-headers")


@haven(__HELP_URL)
async def update_header(ctx: AppCtx, character: VChar):
    """Update the character's RP header."""
    title = f"RP Header: {character.name}"
    modal = _RPHeader(character, title=title[:45])
    await ctx.send_modal(modal)


class _RPHeader(discord.ui.DesignerModal):
    """A modal for setting character RP header details."""

    def __init__(self, character: VChar, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.character = character

        # Since the location field is the embed title, we have to ensure that
        # we don't exceed the maximum length of 256. We use the non-blush text
        # in case the status somehow changes mid-scene. For instance, a mortal
        # might be embraced, or a night might end at a haven, then resume the
        # next night pre-blush. By using the non-blush text, we ensure we don't
        # get any nasty surprises (though name changes mid-scene could still be
        # a problem, which is why we limit the title on show).
        mock_title = inconnu.header.header_title(character.name, NOT_BLUSHED, "")
        max_location_len = 256 - len(mock_title)

        logger.debug("HEADER: Header length, minus location, is {}", len(mock_title))
        logger.debug("HEADER: Max location length: {}", max_location_len)

        self.location_input = discord.ui.InputText(
            placeholder="The location of the current scene",
            value=character.header.location,
            min_length=1,
            max_length=max_location_len,
        )
        self.add_item(discord.ui.Label("Scene Location", self.location_input))

        # Always presenting the select, even if the character isn't a vampire,
        # is more consistent and simplifies callback(). Since we can't disable
        # a ModalItem, we have to get a little tricky with our blush options:
        # we will filter the available options based on the splat. "N/A" must
        # always be default (it's the only option when present), and "Off" is
        # default if not blushed (Off/N/A) in case the character was PREVIOUSLY
        # a Mortal, Thin-Blood, or Humanity > 8.
        blushed = character.header.blush == BlushState.ON
        blush_options = [
            discord.SelectOption(label="On", value=str(BlushState.ON), default=blushed),
            discord.SelectOption(label="Off", value=str(BlushState.OFF), default=not blushed),
            discord.SelectOption(label="N/A", value=str(BlushState.NA), default=True),
        ]
        if character.can_blush:
            blush_options = blush_options[:-1]
        else:
            blush_options = blush_options[-1:]

        self.blush_select = discord.ui.Select(options=blush_options)
        self.add_item(discord.ui.Label("Blush of Life", self.blush_select))

        self.merits_input = discord.ui.InputText(
            placeholder="Merits visible/known to other characters.",
            value=character.header.merits,
            min_length=0,
            max_length=300,
            required=False,
        )
        self.add_item(discord.ui.Label("Apparent Merits", self.merits_input))

        self.flaws_input = discord.ui.InputText(
            placeholder="Flaws visible/known to other characters.",
            value=character.header.flaws,
            min_length=0,
            max_length=300,
            required=False,
        )
        self.add_item(discord.ui.Label("Apparent Flaws", self.flaws_input))

        self.temp_input = discord.ui.InputText(
            placeholder="Temporary effects currently affecting your character.",
            value=character.header.temp,
            max_length=512,
            required=False,
        )
        self.add_item(discord.ui.Label("Temporary Effects", self.temp_input))

    async def callback(self, interaction: discord.Interaction):
        """Set the header and tell the user."""
        location = clean_text((self.location_input.value or "").replace("•", ""))
        if not location:
            # Not responding keeps the modal open, with the player's input intact
            return

        header = self.character.header
        header.location = location
        header.blush = BlushState(int(cast(list[str], self.blush_select.values)[0]))
        header.merits = clean_text(self.merits_input.value or "")
        header.flaws = clean_text(self.flaws_input.value or "")
        header.temp = clean_text(self.temp_input.value or "")

        await asyncio.gather(
            interaction.response.send_message(
                f"Updated **{self.character.name}'s** RP header!", ephemeral=True
            ),
            self.character.save_changes(),
        )
