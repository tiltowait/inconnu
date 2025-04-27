"""interface/macros.py - Macro command interface."""
# pylint: disable=too-many-arguments

import discord
from discord.commands import Option, OptionChoice, SlashCommandGroup, slash_command
from discord.ext import commands

import inconnu


class Macros(commands.Cog, name="Macro Utilities"):
    """Macro manaagement and rolls."""

    @slash_command(contexts={discord.InteractionContextType.guild})
    async def vm(
        self,
        ctx,
        syntax: Option(str, "The macro to roll, plus Hunger and Difficulty"),
        character: inconnu.options.character(),
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
    async def macro_create(
        self,
        ctx,
        name: Option(str, "The macro's name"),
        pool: Option(str, "The dice pool"),
        hunger: Option(
            int,
            "Whether the roll should use the character's current Hunger",
            choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
        ),
        difficulty: Option(
            int, "The default difficulty (may be overridden when rolled)", min_value=0
        ),
        rouses: Option(
            int,
            "The number of Rouse checks (default 0)",
            choices=inconnu.options.ratings(0, 5),
            default=0,
        ),
        reroll_rouses: Option(
            int,
            "Whether to re-roll Rouse checks (default no)",
            choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
            default=0,
        ),
        staining: Option(
            str,
            "Whether the Rouse check can stain",
            choices=[OptionChoice("Yes", "apply"), OptionChoice("No", "show")],
            default="show",
        ),
        hunt: Option(
            int,
            "Make it a hunt macro that lets you slake if successful",
            choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
            default=0,
        ),
        comment: Option(str, "A comment to display with the roll", required=False),
        character: inconnu.options.character(),
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
    async def macro_list(self, ctx, character: inconnu.options.character()):
        """List a character's macros."""
        await inconnu.macros.show(ctx, character)

    @macro.command(name="update")
    async def macro_update(
        self,
        ctx: discord.ApplicationContext,
        macro: Option(str, "The macro's name"),
        parameters: Option(str, "The update parameters (see /help macros)"),
        character: inconnu.options.character("The character who owns the macro"),
    ):
        """Update a macro using PARAMETER=VALUE pairs. Parameter names match macro creation."""
        await inconnu.macros.update(ctx, character, macro, parameters)

    @macro.command(name="delete")
    async def macro_delete(
        self,
        ctx: discord.ApplicationContext,
        macro: Option(str, "The macro to delete"),
        character: inconnu.options.character("The character who owns the macro"),
    ):
        """Delete a macro."""
        await inconnu.macros.delete(ctx, character, macro)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(Macros(bot))
