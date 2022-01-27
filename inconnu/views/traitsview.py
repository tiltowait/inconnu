"""views/traitsview.py - A View for displaying character traits."""

import discord

import inconnu


class TraitsView(inconnu.views.DisablingView):
    """A view that displays character traits."""

    def __init__(self, character, owner):
        super().__init__()
        self.character = character
        self.owner = owner


    @discord.ui.button(label="Traits")
    async def show_traits(self, interaction):
        """Show the traits so long as the user is valid."""
        if interaction.user == self.owner:
            await inconnu.traits.show(interaction, self.character, self.owner)
