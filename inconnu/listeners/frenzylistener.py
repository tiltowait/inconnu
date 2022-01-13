"""listeners/frenzylistener.py - An interface for listening to frenzy roll buttons."""

import asyncio

from discord_ui import Listener

from ..misc.frenzy import frenzy


class FrenzyListener(Listener):
    """Listen to frenzy button events."""

    def __init__(self, user, character, difficulty):
        """
        Args:
            user (int): The Discord ID of the user who may press the button
            character (VChar): The character who will roll frenzy
            difficulty (int): The difficulty of the frenzy
        """
        super().__init__(timeout=60)

        self.user = user
        self.character = character
        self.difficulty = difficulty


    @Listener.button()
    async def respond_to_button(self, btn):
        """Respond to the button event."""
        if btn.author.id != self.user:
            await btn.respond(f"You can't frenzy on {self.character.name}'s behalf.", hidden=True)
            return

        await frenzy(btn, self.difficulty, None, self.character)
        await self.message.disable_components()


    def _stop(self):
        """Stop listening to events."""
        super()._stop()
        asyncio.create_task(self.message.disable_components())
