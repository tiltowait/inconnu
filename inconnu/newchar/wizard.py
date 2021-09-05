"""wizard.py - The new character wizard."""

import discord
from discord_ui import SelectMenu, SelectOption

from ..constants import character_db

class Wizard:
    """A helper class that guides a user through the chargen process."""

    # Used in the select menu. The select menu is not a class variable, because
    # we dynamically create it based on the trait name.
    __RATING_OPTIONS = [
        SelectOption("0", "0 dots"),
        SelectOption("1", "1 dots"),
        SelectOption("2", "2 dots"),
        SelectOption("3", "3 dots"),
        SelectOption("4", "4 dots"),
        SelectOption("5", "5 dots")
    ]

    def __init__(self, ctx, parameters):
        self.core_traits = [
            "Strength", "Dexterity", "Stamina", "Charisma", "Manipulation", "Composure",
            "Intelligence", "Wits", "Resolve", "Athletics", "Brawl", "Craft", "Drive", "Firearms",
            "Larceny", "Melee", "Stealth", "Survival", "AnimalKen", "Etiquette", "Insight",
            "Intimidation", "Leadership", "Performance", "Persuasion", "Streetwise", "Subterfuge",
            "Academics", "Awareness", "Finance", "Investigation", "Medicine", "Occult", "Politics",
            "Science", "Technology"
        ]
        self.ctx = ctx
        self.parameters = parameters

        self.assigned_traits = {}
        self.last_query_message = None


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
        await self.last_query_message.delete()
        self.last_query_message = None

        if len(self.core_traits) == 0:
            # We're finished; create the character
            await self.__finalize_character()
        else:
            await self.__query_trait(f"{trait} set to {rating}.")


    async def __finalize_character(self):
        """Add the character to the database and inform the user they are done."""
        guildid = self.ctx.guild.id
        userid = self.ctx.author.id
        char_type = self.parameters.type
        name = self.parameters.name
        humanity = self.parameters.humanity
        health =  "." *self.parameters.hp
        willpower =  "." *self.parameters.wp

        character_db.add_character(guildid, userid, char_type, name, humanity, 0, health, willpower)
        char_id = character_db.character_id(guildid, userid, name)

        # Need to add the fields one-by-one
        for trait, rating in self.assigned_traits.items():
            character_db.add_trait(guildid, userid, char_id, trait, rating)

        await self.ctx.author.send(f"{name} has been created in {self.ctx.guild.name}!")


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

        self.last_query_message = await self.ctx.author.send(embed=embed, components=[menu])

        # Await the user response
        menu = await self.last_query_message.wait_for("select", self.ctx.bot)
        await menu.respond()

        rating = int(menu.selected_values[0].value)
        await self.__assign_next_trait(rating)
