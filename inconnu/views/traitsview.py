"""views/traitsview.py - A View for displaying character traits."""

import discord

import inconnu
from inconnu.views.disablingview import DisablingView


class TraitsView(DisablingView):
    """A view that displays character traits."""

    def __init__(self, character, owner):
        super().__init__(remove_on_timeout=True)
        self.character = character
        self.owner = owner

    @discord.ui.button(label="Traits", style=discord.ButtonStyle.primary)
    async def show_traits(self, _, interaction):
        """Show the traits so long as the user is valid."""
        if interaction.user == self.owner or interaction.permissions.administrator:
            await inconnu.traits.show(interaction, self.character, player=self.owner)
        else:
            await interaction.response.send_message("You can't click this button.", ephemeral=True)
