"""views/disablingview.py - A view subclass that has a method to disable its items."""

import discord
from discord.ui import Button, Select
from loguru import logger

from ui.views.ephemeralsafeview import EphemeralSafeView


class DisablingView(EphemeralSafeView):
    """A view that can disable all its buttons, save for its link buttons."""

    def __init__(self, timeout: float = 60, remove_on_timeout: bool = False):
        super().__init__(timeout=timeout)
        self.remove_on_timeout = remove_on_timeout

    def link_filter(self) -> list[Button | Select]:
        """The view's buttons and selects, minus link buttons. Includes items
        added after __init__."""
        return [
            item
            for item in self.children
            if isinstance(item, (Button, Select)) and getattr(item, "url", None) is None
        ]

    async def disable_items(self, interaction: discord.Interaction):
        """Disable all non-link items."""
        filtered = self.link_filter()
        for child in filtered:
            child.disabled = True

        await interaction.response.edit_message(view=self)
        self.stop()
        logger.debug("Disabled {} item(s)", len(filtered))

    async def on_timeout(self):
        """Disable the components on timeout, if we have the view's message."""
        message = self.message
        if message is None:
            return

        filtered = self.link_filter()
        if self.remove_on_timeout:
            for item in filtered:
                self.remove_item(item)
            logger.debug("Timeout: Removed {} item(s)", len(filtered))
        else:
            for item in filtered:
                item.disabled = True
            logger.debug("Timeout: Disabled {} item(s)", len(filtered))

        try:
            if isinstance(message, discord.Interaction):
                await message.edit_original_response(view=self)
            else:
                await message.edit(view=self)
        except discord.HTTPException as err:
            # Deleted, or the interaction token expired
            logger.debug("Couldn't edit the view on timeout: {}", err)
