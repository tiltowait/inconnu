"""parse.py - Handles parsing and execution of roll commands."""

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
from discord_ui import Button

from .roll import _roll_pool
from . import dicemoji
from . import reroll
from .. import common
from .. import stats
from ..constants import DAMAGE
from ..vchar import errors, VChar

__UNIVERSAL_TRAITS = ["willpower", "hunger", "humanity"]
__HELP_URL = "https://www.inconnu-bot.com/#/rolls"


async def parse(ctx, raw_syntax: str, character=None):
    """Parse the user's arguments and attempt to roll the dice."""
    syntax = raw_syntax # Save the raw in case we get a character error

    # Comments appear after the first # in a command
    comment = None
    if "#" in syntax:
        syntax, comment = syntax.split("#", 1)
        comment = comment.strip()

    if ctx.guild is None and __needs_character(syntax):
        await common.display_error(ctx, ctx.author.display_name,
            "You cannot roll traits in DMs!",
            __HELP_URL
        )
        return

    args = syntax.split()

    # Determine the character being used, if any
    if ctx.guild is not None:
        # Only guilds have characters
        try:
            if character is not None or __needs_character(syntax):
                character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

        except errors.UnspecifiedCharacterError as err:
            # Two error cases prevent us from continuing:
            #   1. The roll explicitly requires a character (trait roll)
            #   2. The user explicitly supplied a nonexistent character
            if character is not None or __needs_character(syntax):
                # Present the user with a list of their characters
                tip = f"`/vr` `syntax:{raw_syntax}` `character:CHARACTER`"
                character = await common.select_character(ctx, err,
                    __HELP_URL,
                    ("Proper syntax", tip)
                )

                if character is None:
                    # The user never made a selection
                    return

        except errors.CharacterError as err:
            await common.display_error(ctx, ctx.author.display_name, err, __HELP_URL)
            return


    # Attempt to parse the user's roll syntax
    try:
        results = perform_roll(character, *args)
        name = character.name if character is not None else ctx.author.display_name
        await display_outcome(ctx, character, results, comment)

    except (SyntaxError, ValueError) as err:
        name = character.name if character is not None else ctx.author.display_name
        await common.display_error(ctx, name, str(err), __HELP_URL)


async def display_outcome(ctx, character, results, comment, rerolled=False):
    """Display the roll results in a nice embed."""
    # Log the roll. Doing it here captures normal rolls, re-rolls, and macros
    if ctx.guild is not None:
        stats.Stats.log_roll(ctx.guild.id, ctx.author.id, character, results)
    else:
        stats.Stats.log_roll(None, ctx.author.id, character, results)

    # Determine the name for the "author" field
    character_name = None
    if isinstance(character, str):
        character_name = character
    elif isinstance(character, VChar):
        character_name = character.name
    else:
        character_name = ctx.author.display_name

    title = results.main_takeaway
    if not results.is_total_failure and not results.is_bestial:
        title += f" ({results.total_successes})"

    embed = discord.Embed(
        title=title,
        colour=results.embed_color
    )

    # Author line
    author_field = character_name + ("'s reroll" if rerolled else "'s roll")
    if results.difficulty > 0:
        author_field += f" vs diff. {results.difficulty}"
    if results.descriptor is not None:
        author_field += f" ({results.descriptor})"

    embed.set_author(
        name=author_field,
        icon_url=ctx.author.avatar_url
    )

    # Disclosure fields
    normalmoji = dicemoji.emojify(results.normal.dice, False)
    hungermoji = dicemoji.emojify(results.hunger.dice, True)
    embed.add_field(
        name=f"Margin: {results.margin}",
        value=f"{normalmoji} {hungermoji}",
        inline=False
    )

    embed.add_field(name="Pool", value=str(results.pool))
    embed.add_field(name="Hunger", value=str(results.hunger.count))
    embed.add_field(name="Difficulty", value=str(results.difficulty))

    if results.pool_str is not None:
        embed.add_field(name="Pool", value=results.pool_str)

    # Comment
    if comment is not None:
        embed.set_footer(text=comment)

    # Calculate re-roll options and display
    reroll_buttons = __generate_reroll_buttons(results)
    if len(reroll_buttons) == 0 or rerolled:
        if hasattr(ctx, "reply"):
            msg = await ctx.reply(embed=embed)
        else:
            msg = await ctx.respond(embed=embed)
    else:
        try:
            msg = await ctx.respond(embed=embed, components=reroll_buttons)
            rerolled_results = await reroll.wait_for_reroll(ctx, msg, results)
            await display_outcome(ctx, character_name, rerolled_results, comment, rerolled=True)
        except asyncio.exceptions.TimeoutError:
            pass
        finally:
            await msg.disable_components()


def perform_roll(character: VChar, *args):
    """Public interface for __evaluate_syntax() that returns a RollResult."""
    pool_str, roll_params = __evaluate_syntax(character, *args)
    return _roll_pool(roll_params, pool_str)


def __evaluate_syntax(character: VChar, *args):
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
            raise ValueError("Invalid syntax.")

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
                trait_stack.append(match)
            else:
                raise ValueError(str(err)) # pylint: disable=raise-missing-from

        except errors.AmbiguousTraitError as err:
            raise ValueError(err.message) # pylint: disable=raise-missing-from

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

    return SN(pool=compact_stack[0], hunger=compact_stack[1], difficulty=compact_stack[2])


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
    for trait in __UNIVERSAL_TRAITS:
        if trait.startswith(match.lower()):
            matches.append(trait)

    if len(matches) > 1:
        raise ValueError(str(errors.AmbiguousTraitError(match, matches))) # Avoid messy try blocks

    if len(matches) == 1:
        return matches[0]

    return None


def __generate_reroll_buttons(roll_result) -> list:
    """Generate the buttons for Willpower re-rolls."""
    buttons = []

    if roll_result.can_reroll_failures:
        buttons.append(Button("reroll_failures", "Re-Roll Failures"))

    if roll_result.can_maximize_criticals:
        buttons.append(Button("maximize_criticals", "Maximize Crits"))

    if roll_result.can_avoid_messy_critical:
        buttons.append(Button("avoid_messy", "Avoid Messy"))

    if roll_result.can_risky_messy_critical:
        buttons.append(Button("risky", "Risky Avoid Messy"))

    return buttons


def __needs_character(syntax: str):
    """Determines whether a roll needs a character."""
    return re.match(r"[A-z_]", syntax) is not None
