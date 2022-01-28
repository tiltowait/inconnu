"""views/disablingview.py - A view subclass that has a method to disable its items."""

from discord.ui import View


class DisablingView(View):
    """A view that can disable all its buttons."""

    def __init__(self, timeout=60, remove_on_timeout=False):
        super().__init__(timeout=timeout)
        self.remove_on_timeout = remove_on_timeout
        self.message = None

    async def disable_items(self, interaction):
        """Disable all items."""
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(view=self)
        self.stop()


    async def on_timeout(self):
        """Disable the components on timeout, if we have the view's message."""
        if self.message is not None:
            if self.remove_on_timeout:
                self.clear_items()
            else:
                for child in self.children:
                    child.disabled = True

            if hasattr(self.message, "edit"):
                await self.message.edit(view=self)
            else:
                await self.message.edit_original_message(view=self)
