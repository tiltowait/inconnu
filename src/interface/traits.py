"""interface/traits.py - Traits command interface."""
# pylint: disable=no-self-use

import discord
from discord import option
from discord.commands import SlashCommandGroup
from discord.ext import commands

import inconnu


class Traits(commands.Cog, name="Trait Management"):
    """Trait management commands."""

    @commands.user_command(name="Traits", contexts={discord.InteractionContextType.guild})
    async def user_traits(self, ctx, member):
        """Display character traits."""
        await inconnu.traits.show(ctx, None, player=member)

    traits = SlashCommandGroup(
        "traits",
        "Character traits commands.",
        contexts={discord.InteractionContextType.guild},
    )

    @traits.command(name="add")
    @option("traits", description="The traits to add. Ex: Oblivion=4 BloodSorcery=2")
    @inconnu.options.char_option("The character to modify")
    async def traits_add(
        self,
        ctx: discord.ApplicationContext,
        traits: str,
        character: str,
    ):
        """Add one or more traits to a character. To update, use /traits update."""
        await inconnu.traits.add(ctx, character, traits)

    @traits.command(name="list")
    @inconnu.options.char_option("The character to display")
    @inconnu.options.player_option()
    async def traits_list(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        player: discord.Member,
    ):
        """Display a character's traits."""
        await inconnu.traits.show(ctx, character, player=player)

    @traits.command(name="update")
    @option("traits", description="The traits to update. Ex: Oblivion=4 BloodSorcery=2")
    @inconnu.options.char_option("The character to modify")
    async def traits_update(
        self,
        ctx: discord.ApplicationContext,
        traits: str,
        character: str,
    ):
        """Update one or more traits. Traits must already exist (use /traits add)."""
        await inconnu.traits.update(ctx, character, traits)

    @traits.command(name="delete")
    @option("traits", description="The traits to delete. Ex: Oblivion BloodSorcery")
    @inconnu.options.char_option("The character to modify")
    async def delete_traits(
        self,
        ctx: discord.ApplicationContext,
        traits: str,
        character: str,
    ):
        """Remove traits from a character."""
        await inconnu.traits.delete(ctx, character, traits)

    # The following commands are just convenience commands. A specialty is just
    # a 1-point trait, but "how do I add specialties" is a common friction
    # point among users. This command group simplifies the process.

    disciplines = SlashCommandGroup(
        "disciplines",
        "Character disciplines.",
        contexts={discord.InteractionContextType.guild},
    )

    @disciplines.command(name="add")
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
    async def disciplines_update(
        self,
        ctx: discord.ApplicationContext,
        disciplines: str,
        character: str,
    ):
        """Update one or more traits. Traits must already exist (use /traits add)."""
        await inconnu.traits.update(ctx, character, disciplines, True)

    # SPECIALTIES
    specialties = SlashCommandGroup(
        "specialties",
        "Character specialties.",
        contexts={discord.InteractionContextType.guild},
    )

    @specialties.command(name="add")
    @option("specialties", description="The specialties to add. Ex: Performance=Piano,Singing")
    @inconnu.options.char_option("The character to modify")
    async def add_specialties(
        self,
        ctx: discord.ApplicationContext,
        specialties: str,
        character: str,
    ):
        """Add specialties to a character. Can add multiple at a time."""
        await inconnu.specialties.add(
            ctx,
            character,
            specialties,
            inconnu.specialties.Category.SPECIALTY,
        )

    @specialties.command(name="remove")
    @option("specialties", description="The specialties to remove. Ex: Brawl=Kindred,Kine")
    @inconnu.options.char_option("The character to modify")
    async def remove_specialties(
        self,
        ctx: discord.ApplicationContext,
        specialties: str,
        character: str,
    ):
        """Remove specialties from a character. Can remove multiple at a time."""
        await inconnu.specialties.remove(
            ctx,
            character,
            specialties,
            inconnu.specialties.Category.SPECIALTY,
        )

    # POWERS
    powers = SlashCommandGroup(
        "powers",
        "Character specialties.",
        contexts={discord.InteractionContextType.guild},
    )

    @powers.command(name="add")
    @option("powers", description="The powers to add. Ex: Auspex=Premonition,HeightenedSenses")
    @inconnu.options.char_option("The character to modify")
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
    async def remove_powers(
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
