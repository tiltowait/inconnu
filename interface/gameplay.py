"""interface/gameplay.py - Command interface directly related to gameplay."""
# pylint: disable=no-self-use

import discord
from discord import option
from discord.commands import OptionChoice, slash_command
from discord.ext import commands

import inconnu
from inconnu.options import char_option, player_option


class Gameplay(commands.Cog):
    """Gameplay-based commands."""

    def __init__(self, bot):
        self.bot = bot

    # This is the primary roll command. It features the fastest entry and
    # greatest flexibility. However, it can be a stumbling block for new users;
    # hence, the `/roll` command (below) was made.

    @slash_command()
    @option("syntax", description="The roll syntax: POOL HUNGER DIFFICULTY")
    @option("comment", description="A description of the roll", required=False)
    @char_option()
    @player_option()
    async def vr(
        self,
        ctx: discord.ApplicationContext,
        syntax: str,
        comment: str,
        character: str,
        player: discord.Member,
    ):
        """Roll the dice using Thirst syntax. Syntax: POOL HUNGER DIFFICULTY."""
        await inconnu.vr.parse(ctx, syntax, comment, character, player)

    # This beginner-friendly roll command is for users who find the main `/vr`
    # command confusing/difficult. This one is slower to use (especially on
    # mobile) and slightly less flexible; therefore, `/vr` is recommended for
    # most users.

    @slash_command(name="roll")
    @option(
        "pool", description="May be Attribute+Skill or a raw number. Can surge by adding '+ Surge'"
    )
    @option(
        "hunger",
        description="The character's Hunger level",
        choices=[OptionChoice("Use Current (or 0 for Mortals)", "current_hunger")]
        + [OptionChoice(str(n), str(n)) for n in range(0, 6)],
    )
    @option(
        "difficulty",
        description="The target number of successes required",
        choices=[OptionChoice(str(n), n) for n in range(11)],
    )
    @option("comment", description="A comment to display with the roll", required=False)
    @char_option()
    @player_option()
    async def easy_roll(
        self,
        ctx: discord.ApplicationContext,
        pool: str,
        hunger: str,
        difficulty: int,
        comment: str,
        character: str,
        player: discord.Member,
    ):
        """Roll the dice!"""
        syntax = f"{pool} {hunger} {difficulty}"
        char = await inconnu.vr.parse(ctx, syntax, comment, character, player)
        if isinstance(char, inconnu.models.VChar):
            if char.is_vampire:
                if hunger != "current_hunger" and char.hunger == int(hunger):
                    await ctx.respond(
                        (
                            "**Tip:** Select `Use Current` so you don't have "
                            "to remember the number yourself!"
                        ),
                        ephemeral=True,
                    )
            elif hunger != "current_hunger":
                await ctx.respond(
                    "**Tip:** You can select `Use Current` even for mortals.",
                    ephemeral=True,
                )

    @slash_command(contexts={discord.InteractionContextType.guild})
    @char_option("The character to heal")
    async def aggheal(
        self,
        ctx: discord.ApplicationContext,
        character: str,
    ):
        """Heal a character's Aggravated damage, performing three Rouse checks."""
        await inconnu.misc.aggheal(ctx, character)

    @slash_command(contexts={discord.InteractionContextType.guild})
    @char_option("The character to wake")
    async def awaken(
        self,
        ctx: discord.ApplicationContext,
        character: str,
    ):
        """Perform a Rouse check and heal Superficial Willpower damage."""
        await inconnu.misc.awaken(ctx, character)

    @slash_command(contexts={discord.InteractionContextType.guild})
    @option(
        "ministry_alt",
        description="Use the alternate Ministry bane, Cold-Blooded. (Default false)",
        default=False,
    )
    @inconnu.options.char_option("The character to Blush")
    async def bol(
        self,
        ctx: discord.ApplicationContext,
        ministry_alt: bool,
        character: str,
    ):
        """Perform a Blush of Life check, taking Humanity into account."""
        await inconnu.misc.bol(ctx, character, ministry_alt)

    @slash_command(contexts={discord.InteractionContextType.guild})
    @option(
        "difficulty", description="The frenzy difficulty", choices=inconnu.options.ratings(1, 10)
    )
    @option(
        "penalty",
        description="A dice penalty to apply to the roll",
        choices=[
            OptionChoice("Brujah Fury", "brujah"),
            OptionChoice("Malkavian Terror", "malkavian"),
        ],
        required=False,
    )
    @option(
        "bonus",
        description="A dice bonus to apply to the roll",
        choices=[
            "Cold Dead Hunger",
            "The Dream",
            "Gentle Mind",
            "Jewel in the Garden",
            "The Heart of Darkness",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
        ],
        required=False,
    )
    @char_option("The frenzying character")
    async def frenzy(
        self,
        ctx: discord.ApplicationContext,
        difficulty: int,
        penalty: str,
        bonus: str,
        character: str,
    ):
        """Perform a Frenzy check."""
        await inconnu.misc.frenzy(ctx, character, difficulty, penalty, bonus)

    @slash_command(contexts={discord.InteractionContextType.guild})
    @char_option("The character to heal")
    async def mend(
        self,
        ctx,
        character: str,
    ):
        """Mend Superficial damage. For vampires, amount is based on BP and costs a Rouse check."""
        await inconnu.misc.mend(ctx, character)

    @slash_command(contexts={discord.InteractionContextType.guild})
    @option(
        "min_override",
        description="Override the minimum dice to roll (you probably don't want this)",
        choices=inconnu.options.ratings(1, 5),
        default=1,
    )
    @option("lasombra_alt", description="Whether to use Lasombra alt bane", default=False)
    @inconnu.options.char_option("The character undergoing remorse")
    async def remorse(
        self,
        ctx: discord.ApplicationContext,
        min_override: int,
        lasombra_alt: bool,
        character: str,
    ):
        """Perform a Remorse check."""
        await inconnu.misc.remorse(ctx, character, min_override, lasombra_alt)

    @slash_command(contexts={discord.InteractionContextType.guild})
    @option(
        "count",
        description="The number of Rouse checks to make",
        choices=inconnu.options.ratings(1, 5),
        default=1,
    )
    @option(
        "reroll",
        description="Whether to re-roll failures",
        choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
        required=False,
    )
    @option("purpose", description="The reason for the check", required=False)
    @char_option("The character to Rouse")
    async def rouse(
        self,
        ctx: discord.ApplicationContext,
        count: int,
        reroll: int,
        purpose: str,
        character: str,
    ):
        """Perform a Rouse check."""
        await inconnu.misc.rouse(ctx, character, count, purpose, bool(reroll))

    @slash_command(contexts={discord.InteractionContextType.guild})
    @option("amount", description="amount", choices=inconnu.options.ratings(1, 5))
    @char_option("The character feeding")
    async def slake(
        self,
        ctx: discord.ApplicationContext,
        amount: int,
        character: str,
    ):
        """Slake 1 or more Hunger."""
        await inconnu.misc.slake(ctx, character, amount)

    @slash_command(contexts={discord.InteractionContextType.guild})
    @option("delta", description="How many stains to add/subtract", min_value=-10, max_value=10)
    @char_option("The character to stain")
    @player_option()
    async def stain(
        self,
        ctx: discord.ApplicationContext,
        delta: int,
        character: str,
        player: discord.Member,
    ):
        """Apply or remove stains from a character."""
        await inconnu.misc.stain(ctx, character, delta, player=player)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(Gameplay(bot))
