"""wizard.py - The new character wizard."""

import discord

from ..constants import character_db

class Wizard:
    """A helper class that guides a user through the chargen process."""

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


    async def assign_next_trait(self, rating: int):
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


    async def resend_last_query(self, error):
        """Re-send the last query message."""
        await self.__query_trait(error)


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

        # Need to add the fields one-by-one
        for trait, rating in self.assigned_traits.items():
            character_db.add_trait(guildid, userid, name, trait, rating)

        await self.ctx.author.send(f"{name} has been created in {self.ctx.guild.name}!")


    async def __query_trait(self, message=None):
        """Query for the next trait.."""

        description = "This wizard will guide you through the character creation process.\n\n"
        if message is not None:
            description = f"{message}\n\n"

        description += f"Enter the rating for **{self.core_traits[0]}**."

        embed = discord.Embed(
            title=f"Creating {self.parameters.name} on {self.ctx.guild.name}",
            description=description,
            color=0xFF0000,
            icon_url=self.ctx.guild.icon_url
        )
        embed.set_footer(text="Type a number between 0-5.")

        self.last_query_message = await self.ctx.author.send(embed=embed)
