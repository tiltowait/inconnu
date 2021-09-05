"""traits/traitwizard.py - Private trait setter."""

import discord
from discord_ui import SelectMenu, SelectOption

from ..constants import character_db

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

    def __init__(self, ctx, char_name, traits):
        self.ctx = ctx
        self.char_name = char_name
        self.traits = traits
        self.ratings = {}


    async def begin(self):
        """Begin prompting the user."""
        await self.__send_prompt("Incognito trait assignment.")


    async def __send_prompt(self, message=None):
        """Prompt the user."""
        embed = discord.Embed(
            description=message if message is not None else ""
        )
        embed.set_author(
            name=f"{self.char_name} on {self.ctx.guild.name}",
            icon_url=self.ctx.guild.icon_url
        )
        embed.set_footer(text=f"{len(self.traits)} traits remaining")

        menu = SelectMenu("incognito_trait",
            options=self.__RATING_OPTIONS,
            placeholder=f"Select the rating for {self.traits[0]}"
        )

        msg = await self.ctx.author.send(embed=embed, components=[menu])

        # Wait for response
        btn = await msg.wait_for("select", self.ctx.bot, timeout=60)
        await btn.respond()
        await msg.delete()

        # Process response
        trait = self.traits.pop(0)
        rating = int(btn.data["values"][0])

        self.ratings[trait] = rating

        if len(self.traits) == 0:
            await self.__finalize()
        else:
            await self.__send_prompt(f"Set **{trait}** to **{rating}**.")


    async def __finalize(self):
        """Set the traits and tell the user they're all done."""
        guildid = self.ctx.guild.id
        userid = self.ctx.author.id
        charid = character_db.character_id(guildid, userid, self.char_name)

        pretty = []

        for trait, rating in self.ratings.items():
            character_db.add_trait(guildid, userid, charid, trait, rating)
            pretty.append(f"**{trait}**: `{rating}`")

        embed = discord.Embed(
            title="Assignment Complete"
        )
        embed.set_author(
            name=f"{self.char_name} on {self.ctx.guild.name}",
            icon_url=self.ctx.guild.icon_url
        )
        embed.add_field(name="Traits", value="\n".join(pretty))
        await self.ctx.author.send(embed=embed)
