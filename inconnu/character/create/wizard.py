"""character/create/wizard.py - The new character wizard."""
# pylint: disable=too-few-public-methods

import asyncio
import os

import discord
from discord_ui import Button, Listener
from discord_ui.components import LinkButton

from ...constants import INCONNU_ID
from ...settings import Settings
from ...vchar import VChar


class _TraitListener(Listener):
    """Listen to trait selection events."""

    def __init__(self, callback, failback):
        super().__init__(timeout=120)

        self.callback = callback
        self.failback = failback


    @Listener.button()
    async def respond_to_button(self, btn):
        """Respond to the button event and send the button's rating to the callback."""
        await btn.respond()
        await self.callback(int(btn.component.label))


    def _stop(self):
        """Stop listening for events and send the failback."""
        super()._stop()
        asyncio.create_task(self.failback())


class Wizard:
    """A helper class that guides a user through the chargen process."""

    _BUTTONS = [
        [Button(str(n)) for n in range(1,6)],
        [Button("0", color="gray")]
    ]


    def __init__(self, ctx, parameters):
        if "INCONNU_DEV" in os.environ:
            self.core_traits = ["Resolve", "Composure"]
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
        self.msg = None # We will be editing this message instead of sending new ones
        self.parameters = parameters

        if parameters.splat == "vampire":
            self.core_traits.append("Blood Potency")

        self.assigned_traits = {}
        self.use_accessibility = Settings.accessible(ctx.author)


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
        owner = self.ctx.author.id if not self.parameters.spc else INCONNU_ID

        character = VChar.create(self.ctx.guild.id, owner, self.parameters.name)
        character.splat= self.parameters.splat
        character.humanity = self.parameters.humanity
        character.health = "." * self.parameters.hp
        character.willpower = "." * self.parameters.wp

        # Set blood potency when applicable
        if character.splat == "vampire":
            blood_potency = self.assigned_traits["Blood Potency"]
            character.potency = blood_potency
            del self.assigned_traits["Blood Potency"] # Don't want to make this a trait

        # Need to add the traits one-by-one
        for trait, rating in self.assigned_traits.items():
            character.add_trait(trait, rating)

        if self.use_accessibility:
            await self.__finalize_text(character)
        else:
            await self.__finalize_embed(character)


    async def __finalize_text(self, character):
        """Display finalizing message in plain text."""
        contents = f"Success! {character.name} has been created in {self.ctx.guild.name}!"
        contents += f"\nMake a mistake? Use `/traits update` on {self.ctx.guild.name} to fix."
        contents += f"\nWant to add Disciplines? Use `/traits add` on {self.ctx.guild.name}."

        button = LinkButton(
            "https://www.inconnu-bot.com/#/quickstart",
            label="Full Documentation"
        )

        await self.msg.edit(content=contents, components=[button])


    async def __finalize_embed(self, character):
        """Display finalizing message in an embed."""
        embed = discord.Embed(
            title="Success!",
            description=f"**{character.name}** has been created in ***{self.ctx.guild.name}***!",
            colour=discord.Color.blue()
        )
        embed.set_author(
            name=f"Inconnu on {self.ctx.guild.name}",
            icon_url=self.ctx.guild.icon or ""
        )
        embed.add_field(
            name="Make a mistake?",
            value=f"Use `/traits update` on {self.ctx.guild.name} to fix."
        )
        embed.add_field(
            name="Want to add Discipline ratings?",
            value=f"Use `/traits add` on {self.ctx.guild.name}.",
            inline=False
        )

        button = LinkButton(
            "https://www.inconnu-bot.com/#/quickstart",
            label="Full Documentation"
        )

        await self.msg.edit(embed=embed, components=[button])


    async def __query_trait(self, message=None):
        """Query for the next trait."""
        if self.use_accessibility:
            await self.__query_text(message)
        else:
            await self.__query_embed(message)

        if message is None:
            _TraitListener(self.__assign_next_trait, self._timeout).attach_me_to(self.msg)


    async def __query_text(self, message=None):
        """Present the query in plain text."""
        if message is not None:
            contents = [message]
        else:
            contents = ["This wizard will guide you through the character creation process."]
            contents.append("Your character will not be saved until you have entered all traits.")

        contents.append(f"```Select the rating for: {self.core_traits[0]}```")

        if self.msg is None:
            self.msg = await self.ctx.author.send("\n".join(contents), components=Wizard._BUTTONS)
        else:
            await self.msg.edit(content="\n".join(contents))


    async def __query_embed(self, message=None):
        """Present the query in an embed."""
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
            icon_url=self.ctx.guild.icon or ""
        )
        embed.set_footer(text="Your character will not be saved until you have entered all traits.")

        if self.msg is None:
            self.msg = await self.ctx.author.send(embed=embed, components=Wizard._BUTTONS)
        else:
            await self.msg.edit(embed=embed)


    async def _timeout(self):
        """Inform the user they took too long."""
        errmsg = f"Due to inactivity, your chargen on **{self.ctx.guild.name}** has been canceled."
        await self.msg.edit(content=errmsg, embed=None, components=None)
