"""character/create/wizard.py - The new character wizard."""
# pylint: disable=too-few-public-methods

import asyncio
import os

import discord
from discord_ui import SelectMenu, SelectOption
from discord_ui.components import LinkButton

from ...vchar import VChar

class Wizard:
    """A helper class that guides a user through the chargen process."""

    # Used in the select menu. The select menu is not a class variable, because
    # we dynamically create it based on the trait name.
    __RATING_OPTIONS = [
        SelectOption("0", "0 dots"),
        SelectOption("1", "1 dot"),
        SelectOption("2", "2 dots"),
        SelectOption("3", "3 dots"),
        SelectOption("4", "4 dots"),
        SelectOption("5", "5 dots")
    ]

    def __init__(self, ctx, parameters):
        if "INCONNU_DEV" in os.environ:
            self.core_traits = ["Test1", "Test2"]
        else:
            self.core_traits = [
                "Strength", "Dexterity", "Stamina", "Charisma", "Manipulation", "Composure",
                "Intelligence", "Wits", "Resolve", "Athletics", "Brawl", "Craft", "Drive",
                "Firearms", "Larceny", "Melee", "Stealth", "Survival", "AnimalKen", "Etiquette",
                "Insight", "Intimidation", "Leadership", "Performance", "Persuasion", "Streetwise",
                "Subterfuge", "Academics", "Awareness", "Finance", "Investigation", "Medicine",
                "Occult", "Politics", "Science", "Technology"
            ]
        self.ctx = ctx
        self.parameters = parameters

        self.assigned_traits = {}


    async def begin_chargen(self):
        """Start the chargen wizard."""
        await self.__query_trait()


    async def __assign_next_trait(self, rating: int):
        """
        Assign the next trait in the list and display the next trait or finish
        creating the character if finished.

        Args:
            rating (int): The value for the next rating in the list.
        """
        trait = self.core_traits.pop(0)
        self.assigned_traits[trait] = rating

        if len(self.core_traits) == 0:
            # We're finished; create the character
            await self.__finalize_character()
        else:
            await self.__query_trait(f"{trait} set to {rating}.")


    async def __finalize_character(self):
        """Add the character to the database and inform the user they are done."""
        character = VChar.create(self.ctx.guild.id, self.ctx.author.id, self.parameters.name)
        character.splat= self.parameters.splat
        character.humanity = self.parameters.humanity
        character.health = "." * self.parameters.hp
        character.willpower = "." * self.parameters.wp

        # Need to add the traits one-by-one
        for trait, rating in self.assigned_traits.items():
            character.add_trait(trait, rating)

        embed = discord.Embed(
            title="Success!",
            description=f"**{character.name}** has been created in ***{self.ctx.guild.name}***!",
            colour=discord.Color.blue()
        )
        embed.set_author(name=f"Inconnu on {self.ctx.guild.name}", icon_url=self.ctx.guild.icon_url)
        embed.add_field(name="Make a mistake?", value="Use `/traits update` to fix.")

        if self.parameters.splat == "vampire":
            field_name = "Your Blood Potency is currently 0!"
            value = "To update: `/character update potency=X`, where `X` is your Blood Potency."
            embed.add_field(name=field_name, value=value, inline=False)

        button = LinkButton(
            "https://www.inconnu-bot.com/#/quickstart",
            label="Full Documentation"
        )

        await self.ctx.author.send(embed=embed, components=[button])


    async def __query_trait(self, message=None):
        """Query for the next trait.."""

        description = "This wizard will guide you through the character creation process.\n\n"
        if message is not None:
            description = message

        embed = discord.Embed(
            title=f"Select the rating for: {self.core_traits[0]}",
            description=description,
            color=0x7777FF
        )
        embed.set_author(
            name=f"Creating {self.parameters.name} on {self.ctx.guild.name}",
            icon_url=self.ctx.guild.icon_url
        )
        embed.set_footer(text="Your character will not be saved until you have entered all traits.")

        menu = SelectMenu("rating_selector",
            options=self.__RATING_OPTIONS,
            placeholder=f"Select {self.parameters.name}'s {self.core_traits[0]} rating"
        )

        query_msg = await self.ctx.author.send(embed=embed, components=[menu])

        # Await the user response
        try:
            menu = await query_msg.wait_for("select", self.ctx.bot, timeout=60)
            await menu.respond()

            rating = int(menu.selected_values[0])
            await self.__assign_next_trait(rating)

        except asyncio.exceptions.TimeoutError:
            err = f"Due to inactivity, your chargen on **{self.ctx.guild.name}** has been canceled."
            await self.ctx.author.send(err)
