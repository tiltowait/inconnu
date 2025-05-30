"""interface/gameplay.py - Command interface directly related to gameplay."""
# pylint: disable=no-self-use

import discord
from discord import option
from discord.commands import Option, OptionChoice, slash_command
from discord.ext import commands

import inconnu


class Gameplay(commands.Cog):
    """Gameplay-based commands."""

    def __init__(self, bot):
        self.bot = bot

    # This is the primary roll command. It features the fastest entry and
    # greatest flexibility. However, it can be a stumbling block for new users;
    # hence, the `/roll` command (below) was made.

    @slash_command()
    async def vr(
        self,
        ctx: discord.ApplicationContext,
        syntax: Option(str, "The roll syntax: POOL HUNGER DIFFICULTY"),
        comment: Option(str, "A description of the roll", required=False),
        character: inconnu.options.character(),
        player: inconnu.options.player,
    ):
        """Roll the dice using Thirst syntax. Syntax: POOL HUNGER DIFFICULTY."""
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
        hunger: Option(
            str,
            "The character's Hunger level",
            choices=[OptionChoice("Use Current (or 0 for Mortals)", "current_hunger")]
            + [OptionChoice(str(n), str(n)) for n in range(0, 6)],
        ),
        difficulty: Option(
            int,
            "The target number of successes required",
            choices=[OptionChoice(str(n), n) for n in range(11)],
        ),
        comment: Option(str, "A comment to display with the roll", required=False),
        character: inconnu.options.character(),
        player: inconnu.options.player,
    ):
        """Roll the dice!"""
        syntax = f"{pool} {hunger} {difficulty}"
        character = await inconnu.vr.parse(ctx, syntax, comment, character, player)
        if isinstance(character, inconnu.models.VChar):
            if character.is_vampire:
                if hunger != "current_hunger" and character.hunger == int(hunger):
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
    async def aggheal(self, ctx, character: inconnu.options.character("The character to heal")):
        """Heal a character's Aggravated damage, performing three Rouse checks."""
        await inconnu.misc.aggheal(ctx, character)

    @slash_command(contexts={discord.InteractionContextType.guild})
    async def awaken(self, ctx, character: inconnu.options.character("The character to wake")):
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
    async def frenzy(
        self,
        ctx: discord.ApplicationContext,
        difficulty: Option(int, "The frenzy difficulty", choices=inconnu.options.ratings(1, 10)),
        penalty: Option(
            str,
            "A dice penalty to apply to the roll",
            choices=[
                OptionChoice("Brujah Fury", "brujah"),
                OptionChoice("Malkavian Terror", "malkavian"),
            ],
            required=False,
        ),
        bonus: Option(
            str,
            "A dice bonus to apply to the roll",
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
        ),
        character: inconnu.options.character("The frenzying character"),
    ):
        """Perform a Frenzy check."""
        await inconnu.misc.frenzy(ctx, character, difficulty, penalty, bonus)

    @slash_command(contexts={discord.InteractionContextType.guild})
    async def mend(self, ctx, character: inconnu.options.character("The character to heal")):
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
    async def rouse(
        self,
        ctx,
        count: Option(
            int,
            "The number of Rouse checks to make",
            choices=inconnu.options.ratings(1, 5),
            default=1,
        ),
        reroll: Option(
            int,
            "Whether to re-roll failures",
            choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
            required=False,
        ),
        purpose: Option(str, "The reason for the check", required=False),
        character: inconnu.options.character("The character to Rouse"),
    ):
        """Perform a Rouse check."""
        await inconnu.misc.rouse(ctx, character, count, purpose, bool(reroll))

    @slash_command(contexts={discord.InteractionContextType.guild})
    async def slake(
        self,
        ctx: discord.ApplicationContext,
        amount: Option(int, "amount", choices=inconnu.options.ratings(1, 5)),
        character: inconnu.options.character("The character feeding"),
    ):
        """Slake 1 or more Hunger."""
        await inconnu.misc.slake(ctx, character, amount)

    @slash_command(contexts={discord.InteractionContextType.guild})
    async def stain(
        self,
        ctx: discord.ApplicationContext,
        delta: Option(int, "How many stains to add/subtract", min_value=-10, max_value=10),
        character: inconnu.options.character("The character to stain"),
        player: inconnu.options.player,
    ):
        """Apply or remove stains from a character."""
        await inconnu.misc.stain(ctx, character, delta, player=player)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(Gameplay(bot))
