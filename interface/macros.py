"""interface/macros.py - Macro command interface."""
# pylint: disable=too-many-arguments

from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import slash_cog, subslash_cog

import inconnu
from . import debug


class Macros(commands.Cog, name="Macro Utilities"):
    """Macro manaagement and rolls."""

    @ext.check_failure_response("Macros aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="macro",
        description="Macro command group"
        , guild_ids=debug.WHITELIST
    )
    async def macro(self, ctx):
        """Base macro command. Unreachable."""


    @ext.check_failure_response("Macros aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="vm",
        description="Roll a macro.",
        options=[
            SlashOption(str, "syntax",
                description="The macro to roll, plus Hunger and Difficulty",
                required=True
            ),
            SlashOption(str, "character", description="The character that owns the macro")
        ]
        , guild_ids=debug.WHITELIST
    )
    async def macro_roll(self, ctx, syntax: str, character=None):
        """Create a macro."""
        await inconnu.macros.roll(ctx, syntax, character)


    @ext.check_failure_response("Macros aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_cog(
        base_names="macro",
        name="create",
        description="Create a macro.",
        options=[
            SlashOption(str, "name", description="The macro's name", required=True),
            SlashOption(str, "pool", description="The dice pool", required=True),
            SlashOption(int, "hunger", description="Whether the roll should use Hunger",
                choices=[
                    ("Yes", 1), ("No", 0)
                ]
            ),
            SlashOption(int, "difficulty", description="The default difficulty (default 0)"),
            SlashOption(int, "rouses", description="The number of Rouse checks (default 0)",
                choices=[(str(n), n) for n in range(4)]
            ),
            SlashOption(int, "reroll_rouses", description="Whether to re-roll Rouse checks",
                choices=[
                    ("Yes", 1), ("No", 0)
                ]
            ),
            SlashOption(str, "comment", description="A comment to apply to macro rolls"),
            SlashOption(str, "character", description="The character that owns the macro")
        ]
        , guild_ids=debug.WHITELIST
    )
    async def macro_create(
        self,
        ctx,
        name: str,
        pool: str,
        hunger=1,
        difficulty=0,
        rouses=0,
        reroll_rouses=0,
        comment=None,
        character=None
    ):
        """Create a macro."""
        await inconnu.macros.create(
            ctx, name, pool, bool(hunger), difficulty, rouses,
            bool(reroll_rouses), comment, character
        )


    @ext.check_failure_response("Macros aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_cog(
        base_names="macro",
        name="list",
        description="List your macros.",
        options=[
            SlashOption(str, "character", description="The character to display")
        ]
        , guild_ids=debug.WHITELIST
    )
    async def macro_list(self, ctx, character=None):
        """List a character's macros."""
        await inconnu.macros.show(ctx, character)


    @ext.check_failure_response("Macros aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_cog(
        base_names="macro",
        name="delete",
        description="Delete a macro.",
        options=[
            SlashOption(str, "macro", description="The macro to delete", required=True),
            SlashOption(str, "character", description="The character that owns the macro")
        ]
        , guild_ids=debug.WHITELIST
    )
    async def macro_delete(self, ctx, macro: str, character=None):
        """Delete a macro."""
        await inconnu.macros.delete(ctx, macro, character)
