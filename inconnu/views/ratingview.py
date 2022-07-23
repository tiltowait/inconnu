"""views/ratingselector.py - A view for selecting trait ratings."""

import os
import uuid

import discord

from .reportingview import ReportingView

TIMEOUT = 5 if "DEBUG" in os.environ else 300


class RatingView(ReportingView):
    """A View that lets the user select a rating."""

    def __init__(self, callback, failback):
        super().__init__(timeout=TIMEOUT)
        self.callback = callback
        self.failback = failback
        self.ratings = {}
        self.last_interaction = None

        for rating in range(1, 6):
            button_id = str(uuid.uuid4())
            self.ratings[button_id] = rating

            button = discord.ui.Button(
                label=str(rating), custom_id=button_id, style=discord.ButtonStyle.primary, row=0
            )
            button.callback = self.button_pressed
            self.add_item(button)

        # Button 0 is on a separate row. We don't give it a custom ID, because
        # we just fall back to 0 if we can't find the rating anyway
        zero_button = discord.ui.Button(label="0", row=1)
        zero_button.callback = self.button_pressed
        self.add_item(zero_button)

    async def button_pressed(self, interaction):
        """Respond to the button."""
        button_id = interaction.data["custom_id"]
        rating = self.ratings.get(button_id, 0)
        self.last_interaction = interaction

        await self.callback(rating, interaction)

    async def on_timeout(self):
        """Inform the caller that we timed out."""
        await self.failback()
