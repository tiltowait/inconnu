"""interface/gameplay.py - Command interface directly related to gameplay."""

import discord
from discord.commands import Option, OptionChoice, slash_command
from discord.ext import commands

import inconnu


def _ratings(low, high):
    """Creates a list of OptionChoices within the given range, inclusive."""
    return [OptionChoice(str(n), n) for n in range(low, high + 1)]


class Gameplay(commands.Cog):
    """Gameplay-based commands."""

    _CHARACTER_OPTION = Option(str, "The character to use",
        autocomplete=inconnu.available_characters,
        required=False
    )
    _PLAYER_OPTION = Option(discord.Member, "The character's owner (admin only)", required=False)

    # This is the primary roll command. It features the fastest entry and
    # greatest flexibility. However, it can be a stumbling block for new users;
    # hence, the `/roll` command (below) was made.

    @slash_command()
    async def vr(
        self,
        ctx: discord.ApplicationContext,
        syntax: Option(str, "The roll syntax"),
        comment: Option(str, "A description of the roll", required=False),
        character: _CHARACTER_OPTION,
        player: _PLAYER_OPTION
    ):
        """Roll the dice."""
        await inconnu.vr.parse(ctx, syntax, comment, character, player)


    # This beginner-friendly roll command is for users who find the main `/vr`
    # command confusing/difficult. This one is slower to use (especially on
    # mobile) and slightly less flexible; therefore, `/vr` is recommended for
    # most users.

    @slash_command(name="roll")
    async def easy_roll(
        self,
        ctx: discord.ApplicationContext,
        pool: Option(str, "May be Attribute+Skill or a raw number. Can surge by adding '+ Surge'"),
        hunger: Option(str, "The character's Hunger level",
            choices=[OptionChoice("Current Hunger", "hunger")]
                + [OptionChoice(str(n), str(n)) for n in range(1,6)]
        ),
        difficulty: Option(int, "The target number of successes required",
            choices=[OptionChoice(str(n), n) for n in range(11)]
        ),
        comment: Option(str, "A comment to display with the roll", required=False),
        character: _CHARACTER_OPTION,
        player: _PLAYER_OPTION
    ):
        """Roll the dice. Easier (slower) version of /vr."""
        syntax = f"{pool} {hunger} {difficulty}"
        await inconnu.vr.parse(ctx, syntax, comment, character, player)


    @slash_command()
    @commands.guild_only()
    async def aggheal(self, ctx, character: _CHARACTER_OPTION):
        """Heal a character's aggravated damage."""
        await inconnu.misc.aggheal(ctx, character)


    @slash_command()
    @commands.guild_only()
    async def awaken(self, ctx, character: _CHARACTER_OPTION):
        """Perform a Rouse check and heal Superficial Willpower damage."""
        await inconnu.misc.awaken(ctx, character)


    @slash_command()
    @commands.guild_only()
    async def bol(self, ctx, character: _CHARACTER_OPTION):
        """Perform a Blush of Life check, taking Humanity into account."""
        await inconnu.misc.bol(ctx, character)


    @slash_command()
    @commands.guild_only()
    async def cripple(
        self,
        ctx: discord.ApplicationContext,
        damage: Option(int, "The Aggravated damage sustained"),
        character: _CHARACTER_OPTION
    ):
        """Generate a random crippling injury based on Aggravated damage."""
        await inconnu.misc.cripple(ctx, damage, character)


    @slash_command()
    @commands.guild_only()
    async def frenzy(
        self,
        ctx: discord.ApplicationContext,
        difficulty: Option(int, "The frenzy difficulty", choices=_ratings(1, 10)),
        penalty: Option(
            str,
            "Whether there's a penalty to the roll",
            choices=[
                OptionChoice("Brujah Fury", "brujah"),
                OptionChoice("Malkavian Terror", "malkavian")
            ],
            required=False
        ),
        character: _CHARACTER_OPTION
    ):
        """Perform a Frenzy check."""
        await inconnu.misc.frenzy(ctx, difficulty, penalty, character)


    @slash_command()
    @commands.guild_only()
    async def mend(self, ctx, character: _CHARACTER_OPTION):
        """Mend Superficial damage."""
        await inconnu.misc.mend(ctx, character)


    @slash_command()
    @commands.guild_only()
    async def remorse(
        self,
        ctx: discord.ApplicationContext,
        min_override: Option(int, "Override the minimum dice to roll",
            choices=_ratings(1, 5),
            default=1
        ),
        character: _CHARACTER_OPTION,
    ):
        """Perform a remorse check."""
        await inconnu.misc.remorse(ctx, character, min_override)


    @slash_command()
    @commands.guild_only()
    async def resonance(self, ctx):
        """Generate a random Resonance."""
        await inconnu.misc.resonance(ctx)


    @slash_command()
    @commands.guild_only()
    async def rouse(
        self,
        ctx,
        count: Option(int, "The number of Rouse checks to make", choices=_ratings(1, 5)),
        reroll: Option(int, "Whether to re-roll failures",
            choices=[
                OptionChoice("Yes", 1),
                OptionChoice("No", 0)
            ],
            required=False
        ),
        purpose: Option(str, "The reason for the check", required=False),
        character: _CHARACTER_OPTION,
    ):
        """Perform a rouse check."""
        await inconnu.misc.rouse(ctx, count, character, purpose, bool(reroll))


    @slash_command()
    @commands.guild_only()
    async def slake(
        self,
        ctx: discord.ApplicationContext,
        amount: Option(int, "amount", choices=_ratings(1, 5)),
        character: _CHARACTER_OPTION
    ):
        """Slake 1 or more Hunger."""
        await inconnu.misc.slake(ctx, amount, character)


    @slash_command()
    @commands.guild_only()
    async def stain(
        self,
        ctx: discord.ApplicationContext,
        delta: Option(int, "How many stains to add/subtract"),
        character: _CHARACTER_OPTION,
        player: _PLAYER_OPTION
    ):
        """Apply or remove stains from a character."""
        await inconnu.misc.stain(ctx, delta, character, player)
