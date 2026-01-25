"""interface/macros.py - Macro command interface."""
# pylint: disable=too-many-arguments

import discord
from discord import option
from discord.commands import OptionChoice, SlashCommandGroup, slash_command
from discord.ext import commands

import inconnu
from inconnu.options import char_option


class Macros(commands.Cog, name="Macro Utilities"):
    """Macro manaagement and rolls."""

    @slash_command(contexts={discord.InteractionContextType.guild})
    @option("syntax", description="The macro to roll, plus Hunger and Difficulty")
    @char_option()
    async def vm(
        self,
        ctx: discord.ApplicationContext,
        syntax: str,
        character: str,
    ):
        """Roll a macro. You may modify the pool, hunger, and difficulty on the fly."""
        await inconnu.macros.roll(ctx, syntax, character)

    # Macros command group

    macro = SlashCommandGroup(
        "macro",
        "Macro commands.",
        contexts={discord.InteractionContextType.guild},
    )

    @macro.command(name="create")
    @option("name", description="The macro's name")
    @option("pool", description="The dice pool")
    @option(
        "hunger",
        description="Whether the roll should use the character's current Hunger",
        choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
    )
    @option(
        "difficulty",
        description="The default difficulty (may be overridden when rolled)",
        min_value=0,
    )
    @option(
        "rouses",
        description="The number of Rouse checks (default 0)",
        choices=inconnu.options.ratings(0, 5),
        default=0,
    )
    @option(
        "reroll_rouses",
        description="Whether to re-roll Rouse checks (default no)",
        choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
        default=0,
    )
    @option(
        "staining",
        description="Whether the Rouse check can stain",
        choices=[OptionChoice("Yes", "apply"), OptionChoice("No", "show")],
        default="show",
    )
    @option(
        "hunt",
        description="Make it a hunt macro that lets you slake if successful",
        choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
        default=0,
    )
    @option("comment", description="A comment to display with the roll", required=False)
    @char_option()
    async def macro_create(
        self,
        ctx: discord.ApplicationContext,
        name: str,
        pool: str,
        hunger: int,
        difficulty: int,
        rouses: int,
        reroll_rouses: int,
        staining: str,
        hunt: int,
        comment: str,
        character: str,
    ):
        """Create a macro."""
        await inconnu.macros.create(
            ctx,
            character,
            name,
            pool,
            bool(hunger),
            difficulty,
            rouses,
            bool(reroll_rouses),
            staining,
            bool(hunt),
            comment,
        )

    @macro.command(name="list")
    @char_option()
    async def macro_list(
        self,
        ctx: discord.ApplicationContext,
        character: str,
    ):
        """List a character's macros."""
        await inconnu.macros.show(ctx, character)

    @macro.command(name="update")
    @option("macro", description="The macro's name")
    @option("parameters", description="The update parameters (see /help macros)")
    @char_option("The character who owns the macro")
    async def macro_update(
        self,
        ctx: discord.ApplicationContext,
        macro: str,
        parameters: str,
        character: str,
    ):
        """Update a macro using PARAMETER=VALUE pairs. Parameter names match macro creation."""
        await inconnu.macros.update(ctx, character, macro, parameters)

    @macro.command(name="delete")
    @option("macro", description="The macro to delete")
    @char_option("The character who owns the macro")
    async def macro_delete(
        self,
        ctx: discord.ApplicationContext,
        macro: str,
        character: str,
    ):
        """Delete a macro."""
        await inconnu.macros.delete(ctx, character, macro)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(Macros(bot))
