"""views/frenzyview.py - A view that rolls frenzy."""

import discord

import inconnu

from .disablingview import DisablingView


class FrenzyView(DisablingView):
    """A view that rolls frenzy."""

    def __init__(self, character, difficulty):
        super().__init__(timeout=120)
        self.character = character
        self.difficulty = difficulty

        self.frenzy_button = discord.ui.Button(
            label=f"Hunger Frenzy (DC {difficulty})", style=discord.ButtonStyle.danger
        )
        self.frenzy_button.callback = self.frenzy
        self.add_item(self.frenzy_button)

    async def frenzy(self, interaction):
        """Frenzy, if applicable."""
        self.frenzy_button.style = discord.ButtonStyle.secondary
        await self.disable_items(interaction)
        await inconnu.misc.frenzy(interaction, self.difficulty, None, None, self.character)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check that the user is the character's owner."""
        if interaction.user.id == self.character.user:
            return True
        await interaction.response.send_message(
            "This button doesn't belong to you!", ephemeral=True
        )
        return False
