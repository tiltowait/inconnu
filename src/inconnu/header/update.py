"""inconnu/headers/update.py - Update RP headers."""

import asyncio

import discord
from loguru import logger

import inconnu
from ctx import AppCtx
from models import VChar
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/command-reference/characters/rp-headers"


@haven(__HELP_URL)
async def update_header(ctx: AppCtx, character: VChar):
    """Update the character's RP header."""
    title = f"RP Header: {character.name}"
    modal = _RPHeader(character, title=title[:45])
    await ctx.send_modal(modal)


class _RPHeader(discord.ui.DesignerModal):
    """A modal for setting character RP header details."""

    def __init__(self, character: VChar, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.character = character

        # Since the location field is the embed title, we have to ensure that
        # we don't exceed the maximum length of 256. We use the non-blush text
        # in case the status somehow changes mid-scene. For instance, a mortal
        # might be embraced, or a night might end at a haven, then resume the
        # next night pre-blush. By using the non-blush text, we ensure we don't
        # get any nasty surprises (though name changes mid-scene could still be
        # a problem, which is why we limit the title on show).
        mock_title = inconnu.header.header_title(character.name, "Not Blushed", "")
        max_location_len = 256 - len(mock_title)

        logger.debug("HEADER: Header length, minus location, is {}", len(mock_title))
        logger.debug("HEADER: Max location length: {}", max_location_len)

        self.add_item(
            discord.ui.Label(
                "Scene Location",
                discord.ui.InputText(
                    placeholder="The location of the current scene",
                    value=character.header.location,
                    min_length=1,
                    max_length=max_location_len,
                ),
            ),
        )

        # Always presenting the select, even if the character isn't a vampire,
        # is more consistent and simplifies callback(). Since we can't disable
        # a ModalItem, we have to get a little tricky with our blush options:
        # we will filter the available options based on the splat. "N/A" must
        # always be default (it's the only option when present), and "Off" is
        # default if not blushed (0 or -1) in case the character was PREVIOUSLY
        # a Mortal, Thin-Blood, or Humanity > 8.
        blush_options = [
            discord.SelectOption(label="On", value="1", default=self.character.header.blush == 1),
            discord.SelectOption(label="Off", value="0", default=self.character.header.blush < 1),
            discord.SelectOption(label="N/A", value="-1", default=True),
        ]
        if self.character.is_vampire and self.character.humanity < 9:
            blush_options = blush_options[:-1]
        else:
            blush_options = blush_options[-1:]

        self.add_item(discord.ui.Label("Blush of Life", discord.ui.Select(options=blush_options)))

        self.add_item(
            discord.ui.Label(
                "Apparent Merits",
                discord.ui.InputText(
                    placeholder="Merits visible/known to other characters.",
                    value=character.header.merits,
                    min_length=0,
                    max_length=300,
                    required=False,
                ),
            )
        )
        self.add_item(
            discord.ui.Label(
                "Apparent Flaws",
                discord.ui.InputText(
                    placeholder="Flaws visible/known to other characters.",
                    value=character.header.flaws,
                    min_length=0,
                    max_length=300,
                    required=False,
                ),
            )
        )
        self.add_item(
            discord.ui.Label(
                "Temporary Effects",
                discord.ui.InputText(
                    placeholder="Temporary effects currently affecting your character.",
                    value=character.header.temp,
                    max_length=512,
                    required=False,
                ),
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Set the header and tell the user."""
        # TODO: Find out if ModalItem.item is the intended attribute (checker complains)
        self.character.header.location = inconnu.utils.clean_text(self.children[0].item.value)
        self.character.header.blush = int(self.children[1].item.values[0])
        self.character.header.merits = inconnu.utils.clean_text(self.children[2].item.value)
        self.character.header.flaws = inconnu.utils.clean_text(self.children[3].item.value)
        self.character.header.temp = inconnu.utils.clean_text(self.children[4].item.value)

        await asyncio.gather(
            interaction.response.send_message(
                f"Updated **{self.character.name}'s** RP header!", ephemeral=True
            ),
            self.character.save(),
        )
