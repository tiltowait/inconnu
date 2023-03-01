"""parse.py - Handles parsing and execution of roll commands."""
# pylint: disable=too-many-arguments

# When a user rolls, they have two options:
#    * Roll straight numbers (7 3 2 == pool 7, hunger 3, diff 2)
#    * Roll using traits (str+dex 3 2)

# In the latter case, we need to figure out which character they are rolling for.
# If they only have one character, then we will allow them to omit the character
# name; however, if they have more than one, they _MUST_ supply a name. Complicating
# this is the fact they could theoretically supply a name despite not using a
# trait-based roll, so we need to check for the character in either case.

import asyncio
import re
from functools import partial

import discord

import inconnu
from inconnu.models.vchardocs import VCharTrait
from inconnu.roll import Roll
from inconnu.vr.rolldisplay import RollDisplay
from inconnu.vr.rollparser import RollParser
from logger import Logger

__HELP_URL = "https://docs.inconnu.app/guides/quickstart/rolling-with-traits"


async def parse(ctx, raw_syntax: str, comment: str, character: str, player: discord.Member):
    """Parse the user's arguments and attempt to roll the dice."""
    raw_syntax = " ".join(raw_syntax.split())
    syntax = raw_syntax  # Save the raw in case we get a character error
    owner = ctx.user

    # Comments appear after the first # in a command
    if "#" in syntax:
        syntax, comment = syntax.split("#", 1)
        comment = await stringify_mentions(ctx, comment)

    if RollParser.has_invalid_characters(syntax):
        if RollParser.possible_spec_use(syntax):
            fields = [("Trying to roll a specialty?", "Use `skill.spec`, not `skill (spec)`.")]
        else:
            fields = []
        await inconnu.utils.error(ctx, f"Invalid syntax: `{syntax}`.", *fields, ephemeral=False)
        return

    if comment is not None and (comment_len := len(comment)) > 300:
        Logger.debug("VR: Comment is too long")
        await inconnu.utils.error(ctx, f"Comment is too long by {comment_len - 300} characters.")
        return

    if ctx.guild is None and needs_character(syntax):
        await inconnu.utils.error(ctx, "You cannot roll traits in DMs!", help=__HELP_URL)
        return

    # Determine the character being used, if any
    if ctx.guild is not None:
        # Only guilds have characters
        try:
            if character is not None or needs_character(syntax):
                haven = inconnu.utils.Haven(
                    ctx,
                    owner=player,
                    character=character,
                    char_filter=partial(_can_roll, syntax=syntax),
                    tip=f"`/vr` `syntax:{raw_syntax}` `character:CHARACTER`",
                    help=__HELP_URL,
                    errmsg=f"None of your characters can roll `{syntax}`.",
                )
                character = await haven.fetch()
                owner = haven.owner

        except (SyntaxError, LookupError) as err:
            await inconnu.utils.error(ctx, err, help=__HELP_URL)
            return

    # Attempt to parse the user's roll syntax
    try:
        max_hunger = await inconnu.settings.max_hunger(ctx.guild)
        outcome = await perform_roll(character, syntax, max_hunger)
        await display_outcome(ctx, owner, character, outcome, comment)

    except (SyntaxError, ValueError, inconnu.errors.TraitError, inconnu.errors.RollError) as err:
        log_task = inconnu.log.log_event(
            "roll_error", user=ctx.user.id, charid=getattr(character, "id", None), syntax=raw_syntax
        )

        if isinstance(err, inconnu.errors.TraitError):
            view = inconnu.views.TraitsView(character, ctx.user)
            ephemeral = True
        else:
            view = discord.MISSING
            ephemeral = False

        error_task = inconnu.utils.error(
            ctx,
            err,
            ("Your Input", f"/vr syntax:`{raw_syntax}`"),
            author=owner,
            character=character,
            help=__HELP_URL,
            view=view,
            ephemeral=ephemeral,
        )

        await asyncio.gather(log_task, error_task)


def _can_roll(character, syntax):
    """Raises an exception if the traits aren't found."""
    try:
        _ = RollParser(character, syntax)
    except (inconnu.errors.AmbiguousTraitError, inconnu.errors.HungerInPool):
        # It's possible there's no ambiguity on another character
        pass
    except inconnu.errors.TooManyParameters as err:
        # Vampires take the most parameters, so we always want to show the
        # error message if it's too many for a vampire. Mortals, however, have
        # a Hunger 0 inserted, so their parameter count is always one higher.
        if character.is_vampire:
            raise SyntaxError(str(err)) from err

        # We can't use the auto-generated error message for mortals, because
        # the user might have a mortal and a vampire, and the auto-generated
        # message might be confusing given it says Hunger 0.

        msg = (
            f"**Got {err.count - 3} too many parameters!**\n"
            "*If you're adding traits together, don't forget `+` and `-`!*\n"
            f"**Raw:** `{syntax}`"
        )

        if err.count == 4:
            # We don't want to abort early if it's just a case of Hunger being
            # added to a mortal roll, or it won't roll for vampires. This means
            # a user with only mortals will get the most generic error message,
            # but that can't be helped for now.
            msg += "\n\nRemember: Mortals only need `POOL` and `DIFFICULTY`."
            raise inconnu.errors.TooManyParameters(4, msg) from err

        # There are too many parameters even for a vampire, so we'll just fail.
        # This works, because SyntaxErrors aren't handled by Haven.
        msg += "\n\n**Vampires:** `POOL` `HUNGER` `DIFFICULTY`\n**Mortals:** `POOL` `DIFFICULTY`"
        raise SyntaxError(msg) from err


async def display_outcome(
    ctx, player, character: "VChar", results, comment, listener=None, timeout=None
):
    """Display the roll results."""
    roll_display = RollDisplay(ctx, results, comment, character, player, listener, timeout)

    await roll_display.display()


async def perform_roll(character: "VChar", syntax, max_hunger=5):
    """Public interface for __evaluate_syntax() that returns a Roll."""
    parser = RollParser(character, syntax)
    return Roll(parser.pool, parser.hunger, parser.difficulty, max_hunger, parser.pool_str, syntax)


def needs_character(syntax: str):
    """Determines whether a roll needs a character."""
    return re.search(r"[A-z_" + VCharTrait.DELIMITER + "]", syntax) is not None


async def stringify_mentions(ctx, sentence):
    """Replace all raw mentions and channels with their plaintext names."""
    if not sentence:
        return None

    # Use a set to avoid redundant lookups
    if matches := set(re.findall(r"<[@#]!?\d+>", sentence)):
        member_converter = discord.ext.commands.MemberConverter()
        channel_converter = discord.ext.commands.GuildChannelConverter()

        replacements = {}
        failed_lookups = 0

        for match in matches:
            if match in replacements:
                continue

            if "@" in match:
                # Member lookup
                try:
                    replacement = await member_converter.convert(ctx, match)
                    replacements[match] = "@" + replacement.display_name
                except discord.ext.commands.MemberNotFound:
                    pass
            else:
                # Channel lookup
                try:
                    replacement = await channel_converter.convert(ctx, match)
                    replacements[match] = "#" + replacement.name
                except discord.ext.commands.BadArgument:
                    pass

            # Realistically, there should be no failed lookups. If there are,
            # the user is probably trying to lock up the bot. Give them three
            # tries in case there's something weird going on before bailing.
            if not match in replacements:
                failed_lookups += 1
                if failed_lookups == 3:
                    break

        # Replace the items in the original string
        for (match, replacement) in replacements.items():
            sentence = sentence.replace(match, replacement)

    return " ".join(sentence.split())
