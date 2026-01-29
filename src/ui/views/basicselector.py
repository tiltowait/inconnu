"""basicselector.py - A view for selecting basic values."""

import discord

from ui.views.disablingview import DisablingView


class BasicSelector(DisablingView):
    """View that takes arbitrary buttons and tells which was pressed."""

    def __init__(self, *buttons):
        super().__init__()
        self.selected_value = None
        self.interaction = None

        for button in buttons:
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction):
        """Set the selected value to the interaction's custom ID."""
        # Mark the selected button, then disable
        btn_id = interaction.data.get("custom_id")
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == btn_id:
                child.style = discord.ButtonStyle.secondary
                break

        # await self.disable_items(interaction)
        self.interaction = interaction
        self.stop()

        if (selected_values := interaction.data.get("values")) is not None:
            # Select Menu
            self.selected_value = selected_values[0]
        else:
            # Button
            self.selected_value = interaction.data["custom_id"]
