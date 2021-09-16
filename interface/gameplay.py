"""interface/gameplay.py - Command interface directly related to gameplay."""

from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import slash_cog

import inconnu
from . import debug


class Gameplay(commands.Cog):
    """Gameplay-based commands."""

    # This is a legacy command being left in place until Discord mandates its
    # removal. Why? It's slightly faster to use. That's the only reason!

    @commands.command(name="v", aliases=["roll", "r"])
    async def roll(self, ctx):
        """Roll a dice pool, either raw or calculated from traits."""
        await ctx.reply("This command has been removed. Please use `/vr` instead.")


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



    @ext.check_failure_response("Awaken rolls aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="awaken",
        options=[
            SlashOption(str, "character", description="The character waking up"),
        ],
        guild_ids=debug.WHITELIST
    )
    async def awaken(self, ctx, character=None):
        """Perform a Rouse check and heal Superficial Willpower damage."""
        await inconnu.misc.awaken.process(ctx, character)


    @ext.check_failure_response("Frenzy checks aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="frenzy",
        options=[
            SlashOption(int, "difficulty",
                description="The frenzy difficulty",
                choices=[(str(n), n) for n in range(0, 11)],
                required=True
            ),
            SlashOption(str, "character", description="The character resisting frenzy")
        ],
        guild_ids=debug.WHITELIST
    )
    async def frenzy(self, ctx, difficulty: int, character=None):
        """Perform a Frenzy check."""
        await inconnu.misc.frenzy.process(ctx, difficulty, character)


    @ext.check_failure_response("Mending isn't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="mend",
        options=[SlashOption(str, "character", description="The character to be mended")]
        , guild_ids=debug.WHITELIST
    )
    async def mend(self, ctx, character=None):
        """Mend Superficial damage."""
        await inconnu.misc.mend.process(ctx, character)


    @slash_cog(
        name="probability",
        options=[
            SlashOption(str, "roll", description="The pool, difficulty, and hunger", required=True),
            SlashOption(str, "reroll",
                description="The re-roll strategy to use",
                choices=[
                    ("Re-roll Failures", "reroll_failures"),
                    ("Maximize Crits", "maximize_criticals"),
                    ("Avoid Messy", "avoid_messy"),
                    ("Risky Avoid Messy", "risky")
                ]
            ),
            SlashOption(str, "character", description="The character if using traits"),
        ]
        , guild_ids=debug.WHITELIST
    )
    async def probabilities(self, ctx, roll: str, reroll=None, character=None):
        """Calculate outcome probabilities for a given roll."""
        await inconnu.misc.probabilities.process(ctx, roll, reroll, character)


    @ext.check_failure_response("Remorse checks aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="remorse",
        options=[SlashOption(str, "character", description="The character undergoing Remorse")]
        , guild_ids=debug.WHITELIST
    )
    async def remorse(self, ctx, character=None):
        """Perform a remorse check."""
        await inconnu.misc.remorse(ctx, character)


    @slash_cog(name="resonance")
    async def resonance(self, ctx):
        """Generate a random Resonance."""
        await inconnu.misc.resonance.generate(ctx)


    @ext.check_failure_response("Rouse checks aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="rouse",
        options=[
            SlashOption(int, "count", description="The number of Rouse checks to make",
                choices=[(str(n), n) for n in range(1, 6)]
            ),
            SlashOption(str, "character", description="The character performing the check"),
            SlashOption(str, "purpose", description="The reason for the check"),
            SlashOption(str, "reroll", description="Re-roll failures",
                choices=[
                    ("Yes", "true"),
                    ("No", "false")
                ]
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def rouse(self, ctx, count=1, character=None, purpose=None, reroll="false"):
        """Perform a rouse check."""
        await inconnu.misc.rouse(ctx, count, character, purpose, reroll == "true")


    @ext.check_failure_response("You cannot slake in DMs.", hidden=True)
    @commands.guild_only()
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
    async def slake(self, ctx, amount: int, character=None):
        """Slake 1 or more Hunger."""
        await inconnu.misc.slake.process(ctx, amount, character)
