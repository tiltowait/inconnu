"""interface/gameplay.py - Command interface directly related to gameplay."""

from discord.ext import commands
from discord_ui import SlashOption
from discord_ui.cogs import slash_cog

import inconnu
from . import c_help


class Gameplay(commands.Cog):
    """Gameplay-based commands."""

    @commands.command(
        name="v", aliases=["roll", "r"],
        brief=c_help.ROLL_BRIEF,
        description=c_help.ROLL_DESC,
        usage=c_help.ROLL_USAGE,
        help=c_help.ROLL_HELP
    )
    async def roll(self, ctx, *, args=None):
        """Roll a dice pool, either raw or calculated from traits."""
        if args is not None:
            await inconnu.roll.parse(ctx, args)


    @slash_cog(
        name="rouse",
        options=[
            SlashOption(str, "character"),
            SlashOption(int, "count", description="The number of Rouse checks to make")
        ]
        #, guild_ids=[882411164468932609]
    )
    @commands.guild_only()
    async def rouse(self, ctx, character=None, count=1):
        """Perform a rouse check."""
        await inconnu.rousemorse.parse(ctx, "rouse", character, count)


    @slash_cog(
        name="remorse",
        options=[SlashOption(str, "character", description="The character undergoing Remorse")]
        #, guild_ids=[882411164468932609]
    )
    @commands.guild_only()
    async def remorse(self, ctx, character=None):
        """Perform a remorse check."""
        await inconnu.rousemorse.parse(ctx, "remorse", character)


    @slash_cog(name="resonance")
    async def resonance(self, ctx):
        """Generate a random Resonance."""
        await inconnu.resonance.generate(ctx)
