"""views/disablingview.py - A view subclass that has a method to disable its items."""

import discord

from inconnu.views.reportingview import ReportingView


class DisablingView(ReportingView):
    """A view that can disable all its buttons, save for its link buttons."""

    def __init__(self, timeout=60, remove_on_timeout=False):
        super().__init__(timeout=timeout)
        self.remove_on_timeout = remove_on_timeout
        self.link_filter = filter(lambda btn: getattr(btn, "url", None) is None, self.children)
        self.message = None

    async def disable_items(self, interaction):
        """Disable all non-link items."""
        for child in self.link_filter:
            child.disabled = True

        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self):
        """Disable the components on timeout, if we have the view's message."""
        if self.message is not None:
            if self.remove_on_timeout:
                for button in self.link_filter:
                    self.remove_item(button)
            else:
                for child in self.link_filter:
                    child.disabled = True

            try:
                if hasattr(self.message, "edit"):
                    await self.message.edit(view=self)
                else:
                    await self.message.edit_original_response(view=self)
            except discord.NotFound:
                # The message has been deleted
                pass
