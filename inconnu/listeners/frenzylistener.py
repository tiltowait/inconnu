"""listeners/frenzylistener.py - An interface for listening to frenzy roll buttons."""

from discord_ui import Listener

from .disablinglistener import DisablingListener
from ..misc.frenzy import frenzy


class FrenzyListener(DisablingListener):
    """Listen to frenzy button events."""

    def __init__(self, user, character, difficulty):
        """
        Args:
            user (int): The Discord ID of the user who may press the button
            character (VChar): The character who will roll frenzy
            difficulty (int): The difficulty of the frenzy
        """
        super().__init__()

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
