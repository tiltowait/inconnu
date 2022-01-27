"""views/frenzyview.py - A view that rolls frenzy."""

from discord import ButtonStyle
from discord.ui import Button

import inconnu
from .disablingview import DisablingView


class FrenzyView(DisablingView):
    """A view that rolls frenzy."""

    def __init__(self, character, difficulty):
        super().__init__()
        self.character = character
        self.difficulty = difficulty

        frenzy = Button(label=f"Hunger Frenzy (DC {difficulty})", style=ButtonStyle.danger)
        frenzy.callback = self.frenzy
        self.add_item(frenzy)


    async def frenzy(self, interaction):
        """Frenzy, if applicable."""
        if interaction.user.id == self.character.id:
            await inconnu.misc.frenzy(interaction, self.difficulty, None, self.character)
        else:
            if interaction.response.is_done():
                await interaction.followup.send("You can't click this button.", ephemeral=True)
            else:
                await interaction.response.send_message(
                    "You can't click this button.",
                    ephemeral=True
                )
