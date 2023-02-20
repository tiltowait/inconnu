"""interface/traits.py - Traits command interface."""
# pylint: disable=no-self-use

import discord
from discord import option
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

import inconnu


class Traits(commands.Cog, name="Trait Management"):
    """Trait management commands."""

    @commands.user_command(name="Traits")
    @commands.guild_only()
    async def user_traits(self, ctx, member):
        """Display character traits."""
        await inconnu.traits.show(ctx, None, player=member)

    traits = SlashCommandGroup("traits", "Character traits commands.")

    @traits.command(name="add")
    @commands.guild_only()
    async def traits_add(
        self,
        ctx: discord.ApplicationContext,
        traits: Option(str, "The traits to add. Ex: Oblivion=4 BloodSorcery=2"),
        character: inconnu.options.character("The character to modify"),
    ):
        """Add one or more traits to a character. To update, use /traits update."""
        await inconnu.traits.add(ctx, character, traits)

    @traits.command(name="list")
    @commands.guild_only()
    async def traits_list(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character(),
        player: inconnu.options.player,
    ):
        """Display a character's traits."""
        await inconnu.traits.show(ctx, character, player=player)

    @traits.command(name="update")
    @commands.guild_only()
    async def traits_update(
        self,
        ctx: discord.ApplicationContext,
        traits: Option(str, "The traits to update. Ex: Oblivion=3"),
        character: inconnu.options.character("The character to modify"),
    ):
        """Update one or more traits. Traits must already exist (use /traits add)."""
        await inconnu.traits.update(ctx, character, traits)

    @traits.command(name="delete")
    @commands.guild_only()
    async def delete_traits(
        self,
        ctx: discord.ApplicationContext,
        traits: Option(str, "The traits to delete"),
        character: inconnu.options.character("The character to modify"),
    ):
        """Remove traits from a character."""
        await inconnu.traits.delete(ctx, character, traits)

    # The following commands are just convenience commands. A specialty is just
    # a 1-point trait, but "how do I add specialties" is a common friction
    # point among users. This command group simplifies the process.

    disciplines = SlashCommandGroup("disciplines", "Character disciplines.")

    @disciplines.command(name="add")
    @commands.guild_only()
    @option("disciplines", description="The Disciplines to add. Ex: Potence=3 Auspex=2")
    @inconnu.options.char_option("The character to modify")
    async def add_disciplines(
        self,
        ctx: discord.ApplicationContext,
        disciplines: str,
        character: str,
    ):
        await inconnu.traits.add(ctx, character, disciplines, True)

    @disciplines.command(name="remove")
    @commands.guild_only()
    @option("disciplines", description="The Disciplines to remove. Ex: Potence Auspex")
    @inconnu.options.char_option("The character to modify")
    async def remove_disciplines(
        self,
        ctx: discord.ApplicationContext,
        disciplines: str,
        character: str,
    ):
        await inconnu.traits.delete(ctx, character, disciplines, True)

    @disciplines.command(name="update")
    @option("disciplines", description="The Disciplines to update. Ex: Potence=5")
    @inconnu.options.char_option("The character to modify")
    @commands.guild_only()
    async def disciplines_update(
        self,
        ctx: discord.ApplicationContext,
        disciplines: str,
        character: str,
    ):
        """Update one or more traits. Traits must already exist (use /traits add)."""
        await inconnu.traits.update(ctx, character, disciplines, True)

    # SPECIALTIES
    specialties = SlashCommandGroup("specialties", "Character specialties.")

    @specialties.command(name="add")
    @commands.guild_only()
    async def add_specialties(
        self,
        ctx: discord.ApplicationContext,
        specialties: Option(str, "The specialties to add. Ex: Performance=Piano,Singing"),
        character: inconnu.options.character("The character to modify"),
    ):
        """Add specialties to a character. Can add multiple at a time."""
        await inconnu.specialties.add(
            ctx,
            character,
            specialties,
            inconnu.specialties.Category.SPECIALTY,
        )

    @specialties.command(name="remove")
    @commands.guild_only()
    async def remove_specialties(
        self,
        ctx: discord.ApplicationContext,
        specialties: Option(str, "The specialties to remove. Ex: Brawl=Kindred,Kine"),
        character: inconnu.options.character("The character to modify"),
    ):
        """Remove specialties from a character. Can remove multiple at a time."""
        await inconnu.specialties.remove(
            ctx,
            character,
            specialties,
            inconnu.specialties.Category.SPECIALTY,
        )

    # POWERS
    powers = SlashCommandGroup("powers", "Character specialties.")

    @powers.command(name="add")
    @option("powers", description="The powers to add. Ex: Auspex=Premonition,HeightenedSenses")
    @inconnu.options.char_option("The character to modify")
    @commands.guild_only()
    async def add_powers(
        self,
        ctx: discord.ApplicationContext,
        powers: str,
        character: str,
    ):
        """Add powers to a character's Disciplines. Can add multiple at a time."""
        await inconnu.specialties.add(
            ctx,
            character,
            powers,
            inconnu.specialties.Category.POWER,
        )

    @powers.command(name="remove")
    @option("powers", description="The powers to remove. Ex: Auspex=Premonition")
    @inconnu.options.char_option("The character to modify")
    @commands.guild_only()
    async def remove_specialties(
        self,
        ctx: discord.ApplicationContext,
        powers: str,
        character: str,
    ):
        """Remove powers from a character's Disciplines. Can remove multiple at a time."""
        await inconnu.specialties.remove(
            ctx,
            character,
            powers,
            inconnu.specialties.Category.POWER,
        )


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(Traits(bot))
