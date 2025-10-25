"""character/create/wizard.py - The new character wizard."""
# pylint: disable=too-few-public-methods

import asyncio
import os

import discord
from discord.ui import Button
from loguru import logger

import inconnu


class Wizard:
    """A helper class that guides a user through the chargen process."""

    def __init__(self, ctx, parameters):
        if parameters.blank:
            # Make a blank character
            self.core_traits = []
            self.using_dms = False
        else:
            self.using_dms = True
            if "TRUNCATE_COMMANDS" in os.environ:
                # Quicker creation for testing
                self.core_traits = ["Stamina", "Resolve", "Composure"]
            else:
                # Make a character with full traits
                self.core_traits = inconnu.constants.FLAT_TRAITS()

        self.ctx = ctx
        self.msg = None  # We will be editing this message instead of sending new ones
        self.view = inconnu.views.RatingView(self._assign_next_trait, self._timeout)
        self.parameters = parameters

        if parameters.splat == "vampire":
            self.core_traits.append("Blood Potency")

        self.assigned_traits = {}
        self.ctx.bot.wizards += 1
        logger.info("CHARACTER CREATE: Chargen started by {} on {}", ctx.user.name, ctx.guild.name)

    async def begin_chargen(self):
        """Start the chargen wizard."""
        if self.core_traits:
            await self.__query_trait()
        else:
            await self.__finalize_character()

    async def _assign_next_trait(self, rating: int, interaction: discord.Interaction):
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
            await self.__query_trait(message=f"{trait} set to {rating}.", interaction=interaction)

    async def __finalize_character(self):
        """Add the character to the database and inform the user they are done."""
        owner = self.ctx.user.id if not self.parameters.spc else self.ctx.bot.user.id

        character = inconnu.models.VChar(
            guild=self.ctx.guild.id,
            user=owner,
            _name=self.parameters.name,
            splat=self.parameters.splat,
            _humanity=self.parameters.humanity,
            health=self.parameters.hp * inconnu.constants.Damage.NONE,
            willpower=self.parameters.wp * inconnu.constants.Damage.NONE,
            potency=self.assigned_traits.pop("Blood Potency", 0),
        )
        character.assign_traits(self.assigned_traits)
        await character.commit()

        tasks = []
        if self.assigned_traits:
            tasks.append(self.__finalize_embed(character))
        else:
            tasks.append(
                self.edit_message(
                    content=f"Created SPC **{self.parameters.name}**.",
                    embed=None,
                    view=None if self.parameters.splat == "vampire" else discord.MISSING,
                )
            )

        tasks.append(inconnu.char_mgr.register(character))
        tasks.append(
            inconnu.common.report_update(
                ctx=self.ctx,
                character=character,
                title="Character Created",
                message=f"{self.ctx.user.mention} created **{character.name}**.",
                embed=inconnu.traits.embed(self.ctx, character),
            )
        )

        if not self.parameters.spc:
            modal = inconnu.views.ConvictionsModal(character, False)
            tasks.append(self.view.last_interaction.response.send_modal(modal))

        self.view.stop()
        await asyncio.gather(*tasks)
        self.ctx.bot.wizards -= 1

    async def __finalize_embed(self, character):
        """Display finalizing message in an embed."""
        embed = discord.Embed(
            title="Success!",
            description=f"**{character.name}** has been created in ***{self.ctx.guild.name}***!",
            colour=discord.Color.blue(),
        )
        embed.set_author(
            name=f"Inconnu on {self.ctx.guild.name}", icon_url=self.ctx.guild.icon or ""
        )
        embed.add_field(
            name="Make a mistake?", value=f"Use `/traits update` on {self.ctx.guild.name} to fix."
        )
        embed.add_field(
            name="Want to add Discipline ratings or custom traits?",
            value=(
                f"Use `/traits add` on {self.ctx.guild.name}. "
                "Add specialties with `/specialties add`."
            ),
            inline=False,
        )
        embed.set_footer(text="See /help for further details.")

        button = Button(
            label="Full Documentation", url="https://docs.inconnu.app/guides/quickstart"
        )

        await self.edit_message(embed=embed, view=inconnu.views.ReportingView(button))

    async def __query_trait(self, *, interaction: discord.Interaction = None, message: str = None):
        """Query for the next trait."""
        embed = self.__query_embed(message)

        if self.msg is None:
            # First time we're sending the message. Try DMs first and fallback
            # to ephemeral messages if that fails. We prefer DMs so the user
            # always has a copy of the documentation link.
            if self.using_dms:
                try:
                    self.msg = await self.ctx.author.send(embed=embed, view=self.view)
                    # If successful, we post this message in the originating channel
                    await self.ctx.respond(
                        "Please check your DMs! I hope you have your character sheet ready.",
                        ephemeral=True,
                    )
                except discord.errors.Forbidden:
                    self.using_dms = False

            if not self.using_dms:
                self.msg = await self.ctx.respond(embed=embed, view=self.view, ephemeral=True)

        else:
            # Message is being edited
            await interaction.response.edit_message(embed=embed, view=self.view)

    def __query_embed(self, message=None):
        """Present the query in an embed."""
        description = "This wizard will guide you through the character creation process.\n\n"
        if message is not None:
            description = message

        embed = discord.Embed(
            title=f"Select the rating for: {self.core_traits[0]}",
            description=description,
            color=0x7777FF,
        )
        embed.set_author(
            name=f"Creating {self.parameters.name} on {self.ctx.guild.name}",
            icon_url=self.ctx.guild.icon or "",
        )
        embed.set_footer(text="Your character will not be saved until you have entered all traits.")

        return embed

    @property
    def edit_message(self):
        """Get the proper edit method for editing our message outside of an interaction."""
        if self.msg:
            return self.msg.edit
            # return self.msg.edit if self.using_dms else self.msg.edit_original_response
        return self.ctx.respond

    async def _timeout(self):
        """Inform the user they took too long."""
        errmsg = f"Due to inactivity, your chargen on **{self.ctx.guild.name}** has been canceled."
        await self.edit_message(content=errmsg, embed=None, view=None)
        self.ctx.bot.wizards -= 1
        logger.info("CHARACTER CREATE: Timed out")
