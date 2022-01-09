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
from types import SimpleNamespace as SN

import discord
from discord_ui.components import Button

from ..roll_pool import roll_pool
from .rolldisplay import RollDisplay
from .. import common
from ..log import Log
from ..constants import DAMAGE, UNIVERSAL_TRAITS
from ..settings import Settings
from .. import traits
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/rolls"


async def parse(ctx, raw_syntax: str, comment: str, character: str, player: discord.Member):
    """Parse the user's arguments and attempt to roll the dice."""
    syntax = raw_syntax # Save the raw in case we get a character error

    # Comments appear after the first # in a command
    if "#" in syntax:
        syntax, comment = syntax.split("#", 1)
        comment = comment.strip()

    if comment is not None and len(comment) > 300:
        await common.present_error(ctx, f"Comment is too long by {len(comment) - 300} characters.")
        return

    if ctx.guild is None and needs_character(syntax):
        await common.present_error(ctx, "You cannot roll traits in DMs!", help_url=__HELP_URL)
        return

    args = syntax.split()

    # Determine the character being used, if any
    if ctx.guild is not None:
        # Only guilds have characters
        try:
            owner = await common.player_lookup(ctx, player)
            if character is not None or needs_character(syntax):
                tip = f"`/vr` `syntax:{raw_syntax}` `character:CHARACTER`"
                character = await common.fetch_character(
                    ctx, character, tip, __HELP_URL, owner=owner
                )

        except LookupError as err:
            await common.present_error(ctx, err, help_url=__HELP_URL)
            return
        except common.FetchError:
            return


    # Attempt to parse the user's roll syntax
    try:
        results = perform_roll(character, *args)
        await display_outcome(ctx, owner, character, results, comment)

    except (SyntaxError, ValueError, errors.TraitError) as err:
        charid = character.id if character is not None else None
        Log.log("roll_error", user=ctx.author.id, charid=charid, syntax=raw_syntax)

        if isinstance(err, errors.TraitError):
            components = [Button("Show Traits")]
            hidden = True
        else:
            components = None
            hidden = False

        msg = await common.present_error(
            ctx,
            err,
            ("Input", f"/vr syntax:`{raw_syntax}`"),
            author=owner,
            character=character,
            help_url=__HELP_URL,
            components=components,
            hidden=hidden
        )

        # Show the traits button
        if components is not None:
            try:
                btn = await msg.wait_for("button", ctx.bot, timeout=60)

                # No need to check for button ownership; this message is ephemeral
                await traits.show(btn, character, owner)

            except asyncio.exceptions.TimeoutError:
                pass
            finally:
                await msg.disable_components(index=0)


async def display_outcome(ctx, player, character: VChar, results, comment):
    """Display the roll results."""
    roll_display = RollDisplay(ctx, results, comment, character, player)

    if Settings.accessible(ctx.author):
        await roll_display.display(False)
    else:
        await roll_display.display(True)


def perform_roll(character: VChar, *args):
    """Public interface for __evaluate_syntax() that returns a RollResult."""
    pool_str, roll_params = prepare_roll(character, *args)
    return roll_pool(roll_params, pool_str)


def prepare_roll(character: VChar, *args):
    """
    Convert the user's syntax to the standardized format: pool, hunger, diff.
    Args:
        character (VChar) (optional): The character doing the roll
        args (list): The user's syntax

    Valid syntax: snake_case_words, integers, plus, minus.
    This function does not test if the given traits are in the database!

    Raises ValueError if there is trouble querying the database.
    """
    trait_stack, substituted_stack = __substitute_traits(character, *args)
    evaluated_stack = __combine_operators(*substituted_stack)

    # Lop off Hunger and Difficulty from the trait stack, leaving just the pool behind
    while len(trait_stack) > 1 and trait_stack[-2] not in ["+", "-"]:
        trait_stack = trait_stack[:-1]

    pool_str = " ".join(trait_stack)
    return pool_str, evaluated_stack


def __substitute_traits(character: VChar, *args) -> tuple:
    """
    Convert the roll syntax into a stack while simultaneously replacing database
    calls with the appropriate values.

    Valid syntax: snake_case_words, integers, plus, minus.

    Returns (tuple): A stack with expanded trait names and the substituted stack.

    Raises ValueError if there is trouble querying the database.
    """

    # Split the syntax into words and numbers. Pool elements require math operators
    # between them. Optional: If the final two lack operators, they are considered hunger
    # and difficulty.

    # Pass 1: Normalize
    temp_stack = []

    pattern = re.compile(r"^[\w\d\s\+-]+$")

    for argument in args:
        argument = str(argument)

        if not pattern.match(argument):
            raise SyntaxError("Invalid syntax.")

        # Put spaces around the operators so that we can use split()
        argument = re.sub(r"\s*([+-])\s*", r" \g<1> ", argument)

        elements = argument.split()
        temp_stack.extend(elements)

    # Pass 2: Replace database calls with the appropriate values
    substituted_stack = []
    trait_stack = []

    for item in temp_stack:
        if item in ["+", "-"] or item.isdigit():
            substituted_stack.append(item)
            trait_stack.append(item)
            continue

        # User is invoking a trait
        if character is None:
            raise ValueError(f"You must supply a character name to use `{item}`.")

        try:
            trait = character.find_trait(item)
            substituted_stack.append(trait.rating)
            trait_stack.append(trait.name)

        except errors.TraitNotFoundError as err:
            # We allow universal traits
            match = __match_universal_trait(item)
            if match:
                rating = __get_universal_trait(character, match)
                substituted_stack.append(rating)
                trait_stack.append(match.title())
            else:
                raise err

        except errors.AmbiguousTraitError as err:
            raise err

    return trait_stack, substituted_stack


def __combine_operators(*stack):
    """Perform required math operations to produce a <pool> <hunger> <diff> stack."""
    raw_stack = list(stack)
    compact_stack = []

    use_addition = False
    use_subtraction = False

    for item in raw_stack:
        if item == "+":
            use_addition = True
            continue

        if item == "-":
            use_subtraction = True
            continue

        if use_addition and use_subtraction:
            raise SyntaxError("Invalid syntax!")

        item = int(item)

        if not use_addition and not use_subtraction:
            # We have two numbers next to each other, which could either be
            # a syntax error, or they're supplying hunger and/or difficulty.
            # Since we can't know until the end, we will just continue.
            compact_stack.append(item)
        else:
            if len(compact_stack) == 0:
                raise SyntaxError("Invalid syntax!")

            operand = compact_stack.pop()

            if use_addition:
                compact_stack.append(operand + item)
                use_addition = False
            else: # subtraction
                compact_stack.append(operand - item)
                use_subtraction = False

    # Stack operations done.
    if len(compact_stack) > 3:
        raise SyntaxError("Expected pool, hunger, difficulty. You gave more!")

    # Pad out the results with default values of hunger and difficulty, as needed
    padding = [0 for _ in range(3 - len(compact_stack))]
    compact_stack.extend(padding)

    pool = compact_stack[0]
    hunger = compact_stack[1]
    difficulty = compact_stack[2]

    if not 0 <= hunger <= 5:
        # Hunger is outside the accepted range
        raise ValueError("Hunger must be between 0 and 5.")

    hunger = min(pool, hunger) # Make sure we don't roll more hunger dice than the total pool

    return SN(pool=pool, hunger=hunger, difficulty=difficulty)


def __get_universal_trait(character: VChar, trait):
    """Retrieve a universal trait (Hunger, Willpower, Humanity)."""
    value = getattr(character, trait)

    if trait == "willpower":
        # Willpower is a string. Additionally, per RAW only undamaged Willpower
        # may be rolled.
        return value.count(DAMAGE.none)

    # All others are ints
    return value


def __match_universal_trait(match: str):
    """Match a trait to a universal trait. Raise AmbiguousTraitError if ambiguous."""

    # Right now, there are only three universal traits, so this is overkill. However,
    # that number may change in the future, so this flexibility may prove valuable
    # in the long run.
    matches = []
    for trait in UNIVERSAL_TRAITS:
        if trait.startswith(match.lower()):
            matches.append(trait)

    if len(matches) > 1:
        raise ValueError(str(errors.AmbiguousTraitError(match, matches))) # Avoid messy try blocks

    if len(matches) == 1:
        return matches[0]

    return None


def needs_character(syntax: str):
    """Determines whether a roll needs a character."""
    return re.search(r"[A-z_]", syntax) is not None
