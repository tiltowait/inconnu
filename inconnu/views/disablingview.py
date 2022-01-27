"""views/disablingview.py - A view subclass that has a method to disable its items."""

from discord.ui import View


class DisablingView(View):
    """A view that can disable all its buttons."""

    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)


    async def disable_items(self, interaction):
        """Disable all items."""
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(view=self)
        self.stop()
