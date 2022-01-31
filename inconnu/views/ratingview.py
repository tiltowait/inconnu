"""views/ratingselector.py - A view for selecting trait ratings."""

import os

import discord

TIMEOUT = 5 if "DEBUG" in os.environ else 120


class RatingView(discord.ui.View):
    """A View that lets the user select a rating."""

    def __init__(self, callback, failback):
        super().__init__(timeout=TIMEOUT)
        self.callback = callback
        self.failback = failback

        for rating in range(1, 6):
            button = discord.ui.Button(
                label=str(rating),
                custom_id=str(rating),
                style=discord.ButtonStyle.primary,
                row=0
            )
            button.callback = self.button_pressed
            self.add_item(button)

        button = discord.ui.Button(
            label="0",
            custom_id="0",
            row=1
        )
        button.callback = self.button_pressed
        self.add_item(button)


    async def button_pressed(self, interaction):
        """Respond to the button."""
        rating = int(interaction.data["custom_id"])
        await self.callback(rating)


    async def on_timeout(self):
        """Inform the caller that we timed out."""
        await self.failback()
