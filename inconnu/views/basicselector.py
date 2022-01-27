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
        self.selected_value = interaction.data
        print(interaction.data)
