"""interface/gameplay.py - Command interface directly related to gameplay."""

import discord
from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import slash_cog

import inconnu
from . import debug


class Gameplay(commands.Cog):
    """Gameplay-based commands."""

    @commands.command(name="v", aliases=["roll", "r"])
    async def roll(self, ctx):
        """Roll a dice pool, either raw or calculated from traits."""
        await ctx.reply("This command has been removed. Please use `/vr` instead.")


    @slash_cog(
        name="vr", # Called "vr" instead of "roll" for quicker command entry
        options=[
            SlashOption(str, "syntax", description="The roll syntax", required=True),
            SlashOption(str, "comment", description="A description of the roll"),
            SlashOption(str, "character", description="The character performing the roll",
                autocomplete=True, choice_generator=inconnu.available_characters
            ),
            SlashOption(discord.Member, "player", description="The character's owner (admin only)")
        ],
        guild_ids=debug.WHITELIST
    )
    async def slash_roll(self, ctx, syntax: str, comment=None, character=None, player=None):
        """Roll the dice."""
        await inconnu.roll.parse(ctx, syntax, comment, character, player)


    @ext.check_failure_response("Aggravated healing isn't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="aggheal",
        options=[
            SlashOption(str, "character", description="The character to be healed",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def aggheal(self, ctx, character=None):
        """Heal a character's aggravated damage."""
        await inconnu.misc.aggheal(ctx, character)


    @ext.check_failure_response("Awaken rolls aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="awaken",
        options=[
            SlashOption(str, "character", description="The character waking up",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def awaken(self, ctx, character=None):
        """Perform a Rouse check and heal Superficial Willpower damage."""
        await inconnu.misc.awaken(ctx, character)


    @ext.check_failure_response("Blush of Life isn't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="bol",
        options=[
            SlashOption(str, "character", description="The character waking up",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def bol(self, ctx, character=None):
        """Perform a Blush of Life check, taking Humanity into account."""
        await inconnu.misc.bol(ctx, character)


    @slash_cog(
        name="cripple",
        options=[
            SlashOption(int, "damage", description="The Aggravated damage sustained"),
            SlashOption(str, "character", description="The character being injured",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def cripple(self, ctx, damage=None, character=None):
        """Generate a random crippling injury based on Aggravated damage."""
        await inconnu.misc.cripple(ctx, damage, character)


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
            SlashOption(str, "brujah", description="Whether the Brujah bane should apply",
                choices=[
                    ("Yes", "1"),
                    ("No", "0")
                ]
            ),
            SlashOption(str, "character", description="The character resisting frenzy",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def frenzy(self, ctx, difficulty: int, brujah="0", character=None):
        """Perform a Frenzy check."""
        await inconnu.misc.frenzy(ctx, difficulty, bool(int(brujah)), character)


    @ext.check_failure_response("Mending isn't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="mend",
        options=[
            SlashOption(str, "character", description="The character to be mended",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def mend(self, ctx, character=None):
        """Mend Superficial damage."""
        await inconnu.misc.mend(ctx, character)


    @ext.check_failure_response("Remorse checks aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="remorse",
        options=[
            SlashOption(str, "character", description="The character undergoing Remorse",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def remorse(self, ctx, character=None):
        """Perform a remorse check."""
        await inconnu.misc.remorse(ctx, character)


    @slash_cog(name="resonance")
    async def resonance(self, ctx):
        """Generate a random Resonance."""
        await inconnu.misc.resonance(ctx)


    @ext.check_failure_response("Rouse checks aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="rouse",
        options=[
            SlashOption(int, "count", description="The number of Rouse checks to make",
                choices=[(str(n), n) for n in range(1, 6)]
            ),
            SlashOption(str, "character", description="The character performing the check",
                autocomplete=True, choice_generator=inconnu.available_characters
            ),
            SlashOption(str, "purpose", description="The reason for the check"),
            SlashOption(int, "reroll", description="Re-roll failures",
                choices=[
                    ("Yes", 1),
                    ("No", 0)
                ]
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def rouse(self, ctx, count=1, character=None, purpose=None, reroll=0):
        """Perform a rouse check."""
        await inconnu.misc.rouse(ctx, count, character, purpose, bool(reroll))


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
            SlashOption(str, "character", description="The character performing the check",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def slake(self, ctx, amount: int, character=None):
        """Slake 1 or more Hunger."""
        await inconnu.misc.slake(ctx, amount, character)
