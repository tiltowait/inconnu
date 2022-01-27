"""views/ratingselector.py - A view for selecting trait ratings."""

import discord


class RatingView(discord.ui.View):
    """A View that lets the user select a rating."""

    def __init__(self, callback, failback):
        super().__init__(timeout=120)
        self.callback = callback
        self.failback = failback

        for rating in range(1, 6):
            button = discord.ui.Button(
                label=str(rating),
                custom_id=str(rating),
                row=0
            )
            button.callback = self.button_pressed
            self.add_item(button)

        button = discord.ui.Button(
            label="0",
            custom_id="0",
            style=discord.ButtonStyle.secondary, row=1
        )
        button.callback = self.button_pressed
        self.add_item(button)


    async def button_pressed(self, interaction):
        """Respond to the button."""
        await interaction.response.pong()

        rating = int(interaction.data["custom_id"])
        await self.callback(rating)
