"""interface/gameplay.py - Command interface directly related to gameplay."""

from discord.ext import commands
from discord_ui import SlashOption
from discord_ui.cogs import slash_cog

import inconnu
from . import c_help
from . import debug


class Gameplay(commands.Cog):
    """Gameplay-based commands."""

    # This is a legacy command being left in place until Discord mandates its
    # removal. Why? It's slightly faster to use. That's the only reason!

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
        name="vr", # Called "vr" instead of "roll" for quicker command entry
        options=[
            SlashOption(str, "syntax", description="The roll syntax", required=True),
            SlashOption(str, "character", description="The performing the roll")
        ],
        guild_ids=debug.WHITELIST
    )
    async def slash_roll(self, ctx, syntax: str, character=None):
        """Roll the dice."""
        await inconnu.roll.parse(ctx, syntax, character)



    @slash_cog(
        name="awaken",
        options=[
            SlashOption(str, "character", description="The character waking up"),
        ],
        guild_ids=debug.WHITELIST
    )
    @commands.guild_only()
    async def awaken(self, ctx, character=None):
        """Perform a Rouse check and heal Superficial Willpower damage."""
        await inconnu.misc.awaken.process(ctx, character)


    @slash_cog(
        name="mend",
        options=[SlashOption(str, "character", description="The character to be mended")]
        , guild_ids=debug.WHITELIST
    )
    @commands.guild_only()
    async def mend(self, ctx, character=None):
        """Mend Superficial damage."""
        await inconnu.misc.mend.process(ctx, character)


    @slash_cog(
        name="remorse",
        options=[SlashOption(str, "character", description="The character undergoing Remorse")]
        , guild_ids=debug.WHITELIST
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
            SlashOption(str, "character", description="The character performing the check"),
            SlashOption(str, "purpose", description="The reason for the check"),
        ]
        , guild_ids=debug.WHITELIST
    )
    @commands.guild_only()
    async def rouse(self, ctx, count=1, character=None, purpose=None):
        """Perform a rouse check."""
        await inconnu.misc.rousemorse.parse(ctx, "rouse", character, count, purpose)


    @slash_cog(
        name="slake",
        options=[
            SlashOption(int, "amount",
                description="How much Hunger to slake",
                choices=[(str(n), n) for n in range(1, 6)],
                required=True
            ),
            SlashOption(str, "character", description="The character performing the check"),
        ]
        , guild_ids=debug.WHITELIST
    )
    @commands.guild_only()
    async def slake(self, ctx, amount: int, character=None):
        """Slake 1 or more Hunger."""
        await inconnu.misc.slake.process(ctx, amount, character)
