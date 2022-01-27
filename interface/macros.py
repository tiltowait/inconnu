"""interface/macros.py - Macro command interface."""
# pylint: disable=too-many-arguments

import discord
from discord.commands import Option, OptionChoice, SlashCommandGroup, slash_command
from discord.ext import commands

import inconnu


class Macros(commands.Cog, name="Macro Utilities"):
    """Macro manaagement and rolls."""

    _CHARACTER_OPTION = Option(str, "The character to use",
        autocomplete=inconnu.available_characters,
        required=False
    )
    _PLAYER_OPTION = Option(discord.Member, "The character's owner (admin only)", required=False)


    @slash_command()
    @commands.guild_only()
    async def vm(
        self,
        ctx,
        syntax: Option(str, "The macro to roll, plus Hunger and Difficulty"),
        character: _CHARACTER_OPTION
    ):
        """Roll a macro. You may modify the pool, hunger, and difficulty on the fly."""
        await inconnu.macros.roll(ctx, syntax, character)


    # Macros command group

    macro = SlashCommandGroup("macro", "Macro commands.")


    @macro.command(name="create")
    @commands.guild_only()
    async def macro_create(
        self,
        ctx,
        name: Option(str, "The macro's name"),
        pool: Option(str, "The dice pool"),
        hunger: Option(int, "Whether the roll should use the character's current Hunger",
            choices=[
                OptionChoice("Yes", 1), OptionChoice("No", 0)
            ]
        ),
        difficulty: Option(int, "The default difficulty (may be overridden when rolled)",
            min_value=0
        ),
        rouses: Option(int, "The number of Rouse checks (default 0)",
            choices=inconnu.gen_ratings(0, 5),
            default=0
        ),
        reroll_rouses: Option(int, "Whether to re-roll Rouse checks (default no)",
            choices=[
                OptionChoice("Yes", 1), OptionChoice("No", 0)
            ],
            default=0
        ),
        staining: Option(str, "Whether the Rouse check can stain",
            choices=[
                OptionChoice("Yes", "apply"), OptionChoice("No", "show")
            ],
            default="show"
        ),
        comment: Option(str, "A comment to apply to macro rolls", required=False),
        character: _CHARACTER_OPTION
    ):
        """Create a macro."""
        await inconnu.macros.create(
            ctx, name, pool, bool(hunger), difficulty, rouses,
            bool(reroll_rouses), staining, comment, character
        )


    @macro.command(name="list")
    @commands.guild_only()
    async def macro_list(self, ctx, character: _CHARACTER_OPTION):
        """List a character's macros."""
        await inconnu.macros.show(ctx, character)


    @macro.command(name="update")
    @commands.guild_only()
    async def macro_update(
        self,
        ctx: discord.ApplicationContext,
        macro: Option(str, "The macro's name"),
        parameters: Option(str, "The update parameters (see /macro help)"),
        character: _CHARACTER_OPTION
    ):
        """Update a macro using PARAMETER=VALUE pairs. Parameter names match macro creation."""
        await inconnu.macros.update(ctx, macro, parameters, character)


    @macro.command(name="delete")
    @commands.guild_only()
    async def macro_delete(
        self,
        ctx: discord.ApplicationContext,
        macro: Option(str, "The macro to delete"),
        character: _CHARACTER_OPTION
    ):
        """Delete a macro."""
        await inconnu.macros.delete(ctx, macro, character)
