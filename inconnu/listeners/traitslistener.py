"""listeners/traitslistener.py - A Listener for handling Show Traits buttons."""

from discord_ui import Listener

from .disablinglistener import DisablingListener
from .. import traits


class TraitsListener(DisablingListener):
    """A Listener that displays character traits."""

    def __init__(self, character):
        super().__init__()

        self.character = character


    @Listener.button()
    async def respond_to_button(self, btn):
        """Display the character's traits if the valid user presses."""
        if btn.author.id != self.character.user:
            await btn.respond(f"You cannot view {self.character.name}'s traits.")

        await traits.show(btn, self.character, None)
        await self.message.disable_components()
