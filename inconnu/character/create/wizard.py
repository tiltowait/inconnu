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

    def __init__(self, ctx, parameters, accessible):
        if "DEBUG" in os.environ:
            self.core_traits = ["Stamina", "Resolve", "Composure"]
        else:
            self.core_traits = inconnu.constants.FLAT_TRAITS()

        self.ctx = ctx
        self.msg = None # We will be editing this message instead of sending new ones
        self.view = inconnu.views.RatingView(self._assign_next_trait, self._timeout)
        self.parameters = parameters

        if parameters.splat == "vampire":
            self.core_traits.append("Blood Potency")

        self.assigned_traits = {}
        self.use_accessibility = accessible
        self.using_dms = True


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

        character = VChar.create(
            guild=self.ctx.guild.id,
            user=owner,
            name=self.parameters.name,
            splat=self.parameters.splat,
            humanity=self.parameters.humanity,
            health=self.parameters.hp * inconnu.constants.Damage.NONE,
            willpower=self.parameters.wp * inconnu.constants.Damage.NONE,
            potency=self.assigned_traits.pop("Blood Potency", 0),
            traits=self.assigned_traits
        )

        tasks = []

        if self.use_accessibility:
            tasks.append(self.__finalize_text(character))
        else:
            tasks.append(self.__finalize_embed(character))

        tasks.append(inconnu.char_mgr.register(character))
        tasks.append(_deregister_wizard())

        modal = inconnu.views.ConvictionsModal(character, False)
        tasks.append(self.view.last_interaction.response.send_modal(modal))

        # Update channel message
        tasks.append(inconnu.common.report_update(
            ctx=self.ctx,
            character=character,
            title="Character Created",
            message=f"{self.ctx.user.mention} created **{character.name}**."
        ))

        self.view.stop()
        await asyncio.gather(*tasks)


    async def __finalize_text(self, character):
        """Display finalizing message in plain text."""
        contents = f"Success! {character.name} has been created in {self.ctx.guild.name}!"
        contents += f"\nMake a mistake? Use `/traits update` on {self.ctx.guild.name} to fix."
        contents += f"\nWant to add Disciplines? Use `/traits add` on {self.ctx.guild.name}."

        button = Button(
            label="Full Documentation",
            url="https://www.inconnu-bot.com/#/quickstart"
        )

        await self.edit_message(content=contents, view=discord.ui.View(button))


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

        await self.edit_message(embed=embed, view=discord.ui.View(button))


    async def __query_trait(self, message=None):
        """Query for the next trait."""
        if self.use_accessibility:
            msg = { "content": await self.__query_text(message) }
        else:
            msg = { "embed": await self.__query_embed(message) }

        msg["view"] = self.view

        if self.msg is None:
            # First time we're sending the message. Try DMs first and fallback
            # to ephemeral messages if that fails. We prefer DMs so the user
            # always has a copy of the documentation link.
            try:
                self.msg = await self.ctx.author.send(**msg)

                # This won't fire unless the DM was successfully sent
                await self.ctx.respond(
                    "Please check your DMs! I hope you have your character sheet ready.",
                    ephemeral=True
                )
            except discord.errors.Forbidden:
                self.using_dms = False
                self.msg = await self.ctx.respond(**msg, ephemeral=True)
        else:
            await self.edit_message(**msg)


    async def __query_text(self, message=None):
        """Present the query in plain text."""
        if message is not None:
            contents = [message]
        else:
            contents = ["This wizard will guide you through the character creation process."]
            contents.append("Your character will not be saved until you have entered all traits.")

        contents.append(f"```Select the rating for: {self.core_traits[0]}```")

        return "\n".join(contents)


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

        return embed


    @property
    def edit_message(self):
        """Get the proper edit method."""
        return self.msg.edit if self.using_dms else self.msg.edit_original_message


    async def _timeout(self):
        """Inform the user they took too long."""
        errmsg = f"Due to inactivity, your chargen on **{self.ctx.guild.name}** has been canceled."
        await self.edit_message(content=errmsg, embed=None, view=None)
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
