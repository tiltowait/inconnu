"""inconnu/headers/update.py - Update RP headers."""

import asyncio

import discord

import inconnu

__HELP_URL = "https://www.inconnu.app"


async def update_header(ctx: discord.ApplicationContext, character, blush: bool):
    """Update the character's RP header."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild, ctx.user, character)
        modal = _RPHeader(character, blush, title=f"Update RP Header: {character.name}")
        await ctx.send_modal(modal)

    except inconnu.vchar.errors.CharacterNotFoundError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)


class _RPHeader(discord.ui.Modal):
    """A modal for setting character RP header details."""

    def __init__(self, character, blush, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.character = character
        self.blush = blush

        current_header = character.rp_header
        self.add_item(
            discord.ui.InputText(
                label="Scene Location",
                placeholder="The location of the current scene",
                value=current_header.location,
                max_length=200,
            ),
        )
        self.add_item(
            discord.ui.InputText(
                label="Relevant Merits",
                placeholder="Merits characters would know or your scene partner SHOULD know.",
                value=current_header.merits,
                max_length=300,
                required=False,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Relevant Flaws",
                placeholder="Flaws characters would know or your scene partner SHOULD know.",
                value=current_header.flaws,
                max_length=300,
                required=False,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Temporary Effects",
                placeholder="Temporary affects currently affecting your character.",
                value=current_header.temp,
                max_length=300,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Set the header and tell the user."""
        location = " ".join(self.children[0].value.split())
        merits = " ".join(self.children[1].value.split())
        flaws = " ".join(self.children[2].value.split())
        temp = " ".join(self.children[3].value.split())

        new_header = {
            "blush": self.blush,
            "location": location,
            "merits": merits,
            "flaws": flaws,
            "temp": temp,
        }

        await asyncio.gather(
            interaction.response.send_message(
                f"Updated **{self.character.name}'s** RP header!", ephemeral=True
            ),
            self.character.set_rp_header(new_header),
        )
