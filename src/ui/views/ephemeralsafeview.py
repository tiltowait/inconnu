"""views/ephemeralsafeview.py - A view that can still edit its ephemeral message
after a button press."""

import discord

type Editable = discord.Message | discord.Interaction

# Handles that edit through the interaction webhook, which works on ephemeral
# messages
INTERACTION_BACKED = (discord.Interaction, discord.InteractionMessage, discord.WebhookMessage)


class EphemeralSafeView(discord.ui.View):
    """A view whose message handle survives button presses. py-cord replaces
    the handle with the pressed message on every press. That's a plain Message,
    which edits through the channel and so fails on ephemeral messages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # BaseView types its _message too narrowly for an Interaction
        self._handle: Editable | None = None

    # py-cord's property is untyped, so pyright infers a narrower type than
    # py-cord itself assigns (and than display() does, with an Interaction)
    @property
    def message(self) -> Editable | None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """The handle used to edit the view's message."""
        return self._handle

    @message.setter
    def message(self, value: Editable | None):
        """Set the handle, unless it would make an ephemeral message uneditable."""
        if (
            isinstance(value, discord.Message)
            and not isinstance(value, INTERACTION_BACKED)
            and value.flags.ephemeral
            and isinstance(self._handle, INTERACTION_BACKED)
        ):
            return
        self._handle = value
