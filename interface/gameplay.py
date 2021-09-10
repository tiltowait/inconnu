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
        name="mend",
        options=[SlashOption(str, "character", description="The character to be mended")]
        #, guild_ids=[882411164468932609]
    )
    async def mend(self, ctx, character=None):
        """Mend Superficial damage."""
        await inconnu.misc.mend.process(ctx, character)


    @slash_cog(
        name="remorse",
        options=[SlashOption(str, "character", description="The character undergoing Remorse")]
        #, guild_ids=[882411164468932609]
    )
    @commands.guild_only()
    async def remorse(self, ctx, character=None):
        """Perform a remorse check."""
        await inconnu.misc.rousemorse.parse(ctx, "remorse", character)


    @slash_cog(name="resonance")
    async def resonance(self, ctx):
        """Generate a random Resonance."""
        await inconnu.misc.resonance.generate(ctx)


    @slash_cog(
        name="rouse",
        options=[
            SlashOption(int, "count", description="The number of Rouse checks to make"),
            SlashOption(str, "character")
        ]
        #, guild_ids=[882411164468932609]
    )
    @commands.guild_only()
    async def rouse(self, ctx, count=1, character=None):
        """Perform a rouse check."""
        await inconnu.misc.rousemorse.parse(ctx, "rouse", character, count)
