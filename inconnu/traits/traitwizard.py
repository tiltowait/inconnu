"""traits/traitwizard.py - Private trait setter."""
# pylint: disable=too-few-public-methods

import asyncio

import discord
from discord_ui import SelectMenu, SelectOption

from .. import common
from ..settings import Settings


class TraitWizard:
    """A class for private trait-setting."""

    __RATING_OPTIONS = [
        SelectOption("0", "0 dots"),
        SelectOption("1", "1 dots"),
        SelectOption("2", "2 dots"),
        SelectOption("3", "3 dots"),
        SelectOption("4", "4 dots"),
        SelectOption("5", "5 dots")
    ]

    def __init__(self, ctx, character, traits, overwriting):
        self.ctx = ctx
        self.character = character
        self.traits = traits
        self.ratings = {}
        self.overwriting = overwriting


    async def begin(self):
        """Begin prompting the user."""
        await self.__send_prompt("Incognito trait assignment.")


    async def __send_prompt(self, message=None):
        """Prompt the user."""
        menu = SelectMenu("incognito_trait",
            options=self.__RATING_OPTIONS,
            placeholder=f"Select the rating for {self.traits[0]}"
        )

        if Settings.accessible(self.ctx.author):
            msg = await self.__prompt_text(menu, message)
        else:
            msg = await self.__prompt_embed(menu, message)

        # Wait for response
        try:
            btn = await msg.wait_for("select", self.ctx.bot, timeout=60)
            await btn.respond()
            await msg.delete()

            # Process response
            trait = self.traits.pop(0)
            rating = int(btn.selected_values[0])

            self.ratings[trait] = rating

            if len(self.traits) == 0:
                await self.__finalize()
            else:
                await self.__send_prompt(f"Set **{trait}** to **{rating}**.")
        except asyncio.exceptions.TimeoutError:
            await msg.delete()
            err = f"Due to inactivity, **{self.character.name}'s** updates on **{self.ctx.guild.name}** have been canceled."
            await self.ctx.author.send(err)


    async def __prompt_text(self, menu: SelectMenu, message=None):
        """Prompt the user using plain text."""
        contents = [f"{self.character.name}: Trait Assignment"]
        if message is not None:
            contents.append(message + "\n")
        contents.append(f"{common.pluralize(len(self.traits), 'trait')} remaining.")

        return await self.ctx.author.send("\n".join(contents), components=[menu])


    async def __prompt_embed(self, menu: SelectMenu, message=None):
        """Prompt the user using an embed."""
        embed = discord.Embed(
            description=message if message is not None else ""
        )
        embed.set_author(
            name=f"{self.character.name} on {self.ctx.guild.name}",
            icon_url=self.ctx.guild.icon or ""
        )
        embed.set_footer(text=f"{common.pluralize(len(self.traits), 'trait')} remaining")

        return await self.ctx.author.send(embed=embed, components=[menu])


    async def __finalize(self):
        """Set the traits and tell the user they're all done."""
        for trait, rating in self.ratings.items():
            if self.overwriting:
                self.character.update_trait(trait, rating)
            else:
                self.character.add_trait(trait, rating)

        if Settings.accessible(self.ctx.author):
            await self.__finalize_text()
        else:
            await self.__finalize_embed()


    async def __finalize_text(self):
        """Send the finalize message in plain text."""
        contents = ["Assignment Complete\n"]
        contents.append("```css")
        contents.extend([f"{trait}: {rating}" for trait, rating in self.ratings.items()])
        contents.append("```")

        await self.ctx.author.send("\n".join(contents))


    async def __finalize_embed(self):
        """Send the finalize message in an embed."""
        embed = discord.Embed(
            title="Assignment Complete"
        )
        embed.set_author(
            name=f"{self.character.name} on {self.ctx.guild.name}",
            icon_url=self.ctx.guild.icon or ""
        )

        traits = [f"**{trait}:** {rating}" for trait, rating in self.ratings.items()]
        embed.add_field(name="Traits", value="\n".join(traits))

        await self.ctx.author.send(embed=embed)
