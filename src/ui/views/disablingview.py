"""views/disablingview.py - A view subclass that has a method to disable its items."""

import discord
from discord.ui import Button, Select
from loguru import logger

type Editable = discord.Message | discord.Interaction

# Handles that edit through the interaction webhook, which works on ephemeral
# messages
INTERACTION_BACKED = (discord.Interaction, discord.InteractionMessage, discord.WebhookMessage)


class DisablingView(discord.ui.View):
    """A view that can disable all its buttons, save for its link buttons."""

    def __init__(self, timeout: float = 60, remove_on_timeout: bool = False):
        super().__init__(timeout=timeout)
        self.remove_on_timeout = remove_on_timeout
        # BaseView types its _message too narrowly for an Interaction
        self._handle: Editable | None = None

    # py-cord's property is untyped, so pyright infers a narrower type than
    # py-cord itself assigns (and than display() does, with an Interaction)
    @property
    def message(self) -> Editable | None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """The handle used to edit the view's message on timeout."""
        return self._handle

    @message.setter
    def message(self, value: Editable | None):
        """Set the handle, unless it would make an ephemeral message uneditable.
        Each press sets the interaction's plain Message, which edits through the
        channel and so fails on ephemeral messages."""
        if (
            isinstance(value, discord.Message)
            and not isinstance(value, INTERACTION_BACKED)
            and value.flags.ephemeral
            and isinstance(self._handle, INTERACTION_BACKED)
        ):
            return
        self._handle = value

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
        except discord.NotFound:
            # The message has been deleted
            pass
