"""interface/gameplay.py - Command interface directly related to gameplay."""
# pycord: disable=no-self-use

import discord
from discord.commands import Option, OptionChoice, SlashCommandGroup, slash_command
from discord.ext import commands

import inconnu


class Gameplay(commands.Cog):
    """Gameplay-based commands."""

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
        """Roll the dice. Syntax: POOL HUNGER DIFFICULTY."""
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
            choices=[OptionChoice("Current Hunger", "hunger")]
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
        """Roll the dice. Easier (slower) version of /vr."""
        syntax = f"{pool} {hunger} {difficulty}"
        await inconnu.vr.parse(ctx, syntax, comment, character, player)

    @slash_command()
    @commands.guild_only()
    async def aggheal(self, ctx, character: inconnu.options.character("The character to heal")):
        """Heal a character's Aggravated damage."""
        await inconnu.misc.aggheal(ctx, character)

    @slash_command()
    @commands.guild_only()
    async def awaken(self, ctx, character: inconnu.options.character("The character to wake")):
        """Perform a Rouse check and heal Superficial Willpower damage."""
        await inconnu.misc.awaken(ctx, character)

    @slash_command()
    @commands.guild_only()
    async def bol(self, ctx, character: inconnu.options.character("The character to Blush")):
        """Perform a Blush of Life check, taking Humanity into account."""
        await inconnu.misc.bol(ctx, character)

    @slash_command()
    @commands.guild_only()
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
                "1",
                "2",
                "3",
                "4",
                "5",
            ],
            required=False,
        ),
        character: inconnu.options.character("The frenzying character"),
    ):
        """Perform a Frenzy check."""
        await inconnu.misc.frenzy(ctx, difficulty, penalty, bonus, character)

    @slash_command()
    @commands.guild_only()
    async def mend(self, ctx, character: inconnu.options.character("The character to heal")):
        """Mend Superficial damage."""
        await inconnu.misc.mend(ctx, character)

    @slash_command()
    @commands.guild_only()
    async def remorse(
        self,
        ctx: discord.ApplicationContext,
        min_override: Option(
            int,
            "Override the minimum dice to roll (you probably don't want this)",
            choices=inconnu.options.ratings(1, 5),
            default=1,
        ),
        character: inconnu.options.character("The character undergoing remorse"),
    ):
        """Perform a Remorse check."""
        await inconnu.misc.remorse(ctx, character, min_override)

    @slash_command()
    @commands.guild_only()
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
        await inconnu.misc.rouse(ctx, count, character, purpose, bool(reroll))

    @slash_command()
    @commands.guild_only()
    async def slake(
        self,
        ctx: discord.ApplicationContext,
        amount: Option(int, "amount", choices=inconnu.options.ratings(1, 5)),
        character: inconnu.options.character("The character feeding"),
    ):
        """Slake 1 or more Hunger."""
        await inconnu.misc.slake(ctx, amount, character)

    @slash_command()
    @commands.guild_only()
    async def stain(
        self,
        ctx: discord.ApplicationContext,
        delta: Option(int, "How many stains to add/subtract"),
        character: inconnu.options.character("The character to stain"),
        player: inconnu.options.player,
    ):
        """Apply or remove stains from a character."""
        await inconnu.misc.stain(ctx, delta, character, player)

    # "Headers" are used in PbP RP. For now, they are just in testing on a
    # single server (plus dev server) for admin users.

    HEADER_DEBUG_GUILDS = [826628660450689074, 676333549720174605]

    @slash_command(debug_guilds=HEADER_DEBUG_GUILDS)
    @discord.default_permissions(administrator=True)
    async def header(
        self,
        ctx: discord.ApplicationContext,
        blush: Option(
            int,
            "OVERRIDE: Is Blush of Life active?",
            choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
            required=False,
        ),
        location: Option(str, "OVERRIDE: Where the scene is taking place", required=False),
        merits: Option(str, "OVERRIDE: Obvious/important merits", required=False),
        flaws: Option(str, "OVERRIDE: Obvious/important flaws", required=False),
        character: inconnu.options.character("The character whose header to post"),
    ):
        """Display you character's RP header."""
        await inconnu.header.show_header(
            ctx, character, blush=blush, location=location, merits=merits, flaws=flaws
        )

    header_update = SlashCommandGroup("update", "Update commands")

    @header_update.command(name="header", debug_guilds=HEADER_DEBUG_GUILDS)
    @discord.default_permissions(administrator=True)
    async def update_header(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character whose header to update", required=True),
        blush: Option(
            int,
            "Is Blush of Life active?",
            choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
        ),
    ):
        """Update your character's RP header."""
        await inconnu.header.update_header(ctx, character, bool(blush))


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(Gameplay(bot))
