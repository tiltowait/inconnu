"""interface/gameplay.py - Command interface directly related to gameplay."""

import discord
from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import slash_command

import inconnu
from . import debug


class Gameplay(commands.Cog):
    """Gameplay-based commands."""

    # This is the primary roll command. It features the fastest entry and
    # greatest flexibility. However, it can be a stumbling block for new users;
    # hence, the `/roll` command (below) was made.

    @slash_command(
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
        await inconnu.vr.parse(ctx, syntax, comment, character, player)


    # This beginner-friendly roll command is for users who find the main `/vr`
    # command confusing/difficult. This one is slower to use (especially on
    # mobile) and slightly less flexible; therefore, `/vr` is recommended for
    # most users.

    @slash_command(
        name="roll",
        options=[
            SlashOption(
                str,
                "pool",
                description="May be Attribute+Skill or a raw number. Can surge by adding '+ Surge'",
                required=True
            ),
            SlashOption(
                str,
                "hunger",
                description="The character's Hunger level",
                choices=[("Current Hunger", "hunger")] + [(str(n), str(n)) for n in range(1,6)],
                required=True
            ),
            SlashOption(
                int,
                "difficulty",
                description="The target number of successes required",
                choices=[(str(n), n) for n in range(11)],
                required=True
            ),
            SlashOption(
                str,
                "comment",
                description="A comment to display with the roll",
                required=False
            ),
            SlashOption(
                str,
                "character",
                description="The character performing the roll",
                autocomplete=False,
                choice_generator=inconnu.available_characters
            ),
            SlashOption(discord.Member, "player", description="The character's owner (admin only)"),
        ],
        guild_ids=debug.WHITELIST
    )
    async def easy_roll(self,
        ctx,
        pool: str,
        hunger: str,
        difficulty: int,
        comment: str = None,
        character: str = None,
        player: discord.Member = None
    ):
        """Roll the dice. Easier (slower) version of /vr."""
        syntax = f"{pool} {hunger} {difficulty}"
        await inconnu.vr.parse(ctx, syntax, comment, character, player)


    @ext.check_failed("Aggravated healing isn't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_command(
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


    @ext.check_failed("Awaken rolls aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_command(
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


    @ext.check_failed("Blush of Life isn't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_command(
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


    @slash_command(
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


    @ext.check_failed("Frenzy checks aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_command(
        name="frenzy",
        options=[
            SlashOption(int, "difficulty",
                description="The frenzy difficulty",
                choices=[(str(n), n) for n in range(1, 11)],
                required=True
            ),
            SlashOption(str, "penalty", description="Whether there's a penalty to the roll",
                choices=[
                    ("Brujah Fury", "brujah"),
                    ("Malkavian Terror", "malkavian")
                ]
            ),
            SlashOption(str, "character", description="The character resisting frenzy",
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def frenzy(self, ctx, difficulty: int, penalty=None, character=None):
        """Perform a Frenzy check."""
        await inconnu.misc.frenzy(ctx, difficulty, penalty, character)


    @ext.check_failed("Mending isn't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_command(
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


    @ext.check_failed("Remorse checks aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_command(
        name="remorse",
        options=[
            SlashOption(str, "character", description="The character undergoing Remorse",
                autocomplete=True, choice_generator=inconnu.available_characters
            ),
            SlashOption(int, "min_override", description="Override the minimum dice to roll",
                choices=[(str(n), n) for n in range(1, 5)]
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def remorse(self, ctx, character=None, min_override=1):
        """Perform a remorse check."""
        await inconnu.misc.remorse(ctx, character, min_override)


    @slash_command(name="resonance")
    async def resonance(self, ctx):
        """Generate a random Resonance."""
        await inconnu.misc.resonance(ctx)


    @ext.check_failed("Rouse checks aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_command(
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


    @ext.check_failed("You cannot slake in DMs.", hidden=True)
    @commands.guild_only()
    @slash_command(
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


    @ext.check_failed("You cannot add stains in DMs.", hidden=True)
    @commands.guild_only()
    @slash_command(
        name="stain",
        options=[
            SlashOption(int, "delta", description="How many stains to add/subtract", required=True),
            SlashOption(str, "character", description="The character performing the check",
                autocomplete=True, choice_generator=inconnu.available_characters
            ),
            SlashOption(discord.Member, "player", description="The character's owner (admin only)")
        ],
        guild_ids=debug.WHITELIST
    )
    async def stain(self, ctx, delta: int, character=None, player=None):
        """Apply or remove stains from a character."""
        await inconnu.misc.stain(ctx, delta, character, player)
