"""basicselector.py - A view for selecting basic values."""

from .disablingview import DisablingView


class BasicSelector(DisablingView):
    """View that takes arbitrary buttons and tells which was pressed."""

    def __init__(self, *buttons):
        super().__init__()
        self.selected_value = None

        for button in buttons:
            button.callback = self.button_callback
            self.add_item(button)


    async def button_callback(self, interaction):
        """Set the selected value to the interaction's custom ID."""
        await self.disable_items(interaction)

        if (selected_values := interaction.data.get("values")) is not None:
            # Select Menu
            self.selected_value = selected_values[0]
        else:
            # Button
            self.selected_value = interaction.data["custom_id"]
