"""listeners/disablinglistener.py - Base Listener subclass that disables message components."""

import asyncio

from discord_ui import Listener


class DisablingListener(Listener):
    """A Listener subclass that disables its message components when stopped."""

    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)


    def _stop(self):
        """Stop listening and disable the message components."""
        super()._stop()
        asyncio.create_task(self.message.disable_components())
