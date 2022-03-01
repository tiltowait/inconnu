"""character/create/wizard.py - The new character wizard."""
# pylint: disable=too-few-public-methods

import asyncio
import os
import threading

import discord
from discord.ui import Button

import inconnu
from inconnu.vchar import VChar


class Wizard:
    """A helper class that guides a user through the chargen process."""

    def __init__(self, ctx, parameters):
        if "DEBUG" in os.environ:
            self.core_traits = ["Resolve", "Composure"]
        else:
            self.core_traits = inconnu.constants.FLAT_TRAITS()

        self.ctx = ctx
        self.msg = None # We will be editing this message instead of sending new ones
        self.view = inconnu.views.RatingView(self._assign_next_trait, self._timeout)
        self.parameters = parameters

        if parameters.splat == "vampire":
            self.core_traits.append("Blood Potency")

        self.assigned_traits = {}
        self.use_accessibility = inconnu.settings.accessible(ctx.user)


    async def begin_chargen(self):
        """Start the chargen wizard."""
        await asyncio.gather(_register_wizard(), self.__query_trait())


    async def _assign_next_trait(self, rating: int):
        """
        Assign the next trait in the list and display the next trait or finish
        creating the character if finished.

        Args:
            rating (int): The value for the next rating in the list.
        """
        trait = self.core_traits.pop(0)
        self.assigned_traits[trait] = rating

        if not self.core_traits:
            # We're finished; create the character
            await self.__finalize_character()
        else:
            await self.__query_trait(f"{trait} set to {rating}.")


    async def __finalize_character(self):
        """Add the character to the database and inform the user they are done."""
        owner = self.ctx.user.id if not self.parameters.spc else inconnu.constants.INCONNU_ID

        character = VChar.create(self.ctx.guild.id, owner, self.parameters.name)
        character.splat= self.parameters.splat
        character.humanity = self.parameters.humanity
        character.health = "." * self.parameters.hp
        character.willpower = "." * self.parameters.wp

        # Set blood potency when applicable
        if character.is_vampire:
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

        self.view.stop()
        await _deregister_wizard()


    async def __finalize_text(self, character):
        """Display finalizing message in plain text."""
        contents = f"Success! {character.name} has been created in {self.ctx.guild.name}!"
        contents += f"\nMake a mistake? Use `/traits update` on {self.ctx.guild.name} to fix."
        contents += f"\nWant to add Disciplines? Use `/traits add` on {self.ctx.guild.name}."

        button = Button(
            label="Full Documentation",
            url="https://www.inconnu-bot.com/#/quickstart"
        )

        await self.msg.edit(content=contents, view=discord.ui.View(button))


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

        button = Button(
            label="Full Documentation",
            url="https://www.inconnu-bot.com/#/quickstart"
        )

        await self.msg.edit(embed=embed, view=discord.ui.View(button))


    async def __query_trait(self, message=None):
        """Query for the next trait."""
        if self.use_accessibility:
            await self.__query_text(message)
        else:
            await self.__query_embed(message)


    async def __query_text(self, message=None):
        """Present the query in plain text."""
        if message is not None:
            contents = [message]
        else:
            contents = ["This wizard will guide you through the character creation process."]
            contents.append("Your character will not be saved until you have entered all traits.")

        contents.append(f"```Select the rating for: {self.core_traits[0]}```")

        if self.msg is None:
            self.msg = await self.ctx.user.send("\n".join(contents), view=self.view)
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
            self.msg = await self.ctx.user.send(embed=embed, view=self.view)
        else:
            await self.msg.edit(embed=embed)


    async def _timeout(self):
        """Inform the user they took too long."""
        errmsg = f"Due to inactivity, your chargen on **{self.ctx.guild.name}** has been canceled."
        await self.msg.edit(content=errmsg, embed=None, view=None)
        await _deregister_wizard()


# When we deploy a new build of the bot, we want to avoid doing so while someone
# is creating a character. To prevent this, we maintain a lock file that tracks
# the number of actively running wizards. On deployment, if the count is 0, then
# the deployment will proceed.

async def _register_wizard():
    """Increment the chargen counter."""
    await __modify_lock(1)


async def _deregister_wizard():
    """Decrement the chargen counter."""
    await __modify_lock(-1)


async def __modify_lock(delta):
    """Modify the chargen counter."""
    lockfile = ".wizard.lock"
    lock = threading.Lock()

    with lock:
        if not os.path.exists(lockfile):
            open(lockfile, "w", encoding="utf8").close() # pylint: disable=consider-using-with

        with open(lockfile, "r+", encoding="utf8") as registration:
            try:
                counter = int(registration.readline())
            except ValueError:
                counter = 0

            counter = max(0, counter + delta)

            registration.seek(0)
            registration.write(str(counter))
            registration.truncate()
