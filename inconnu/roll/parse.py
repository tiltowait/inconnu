"""parse.py - Handles parsing and execution of roll commands."""

# When a user rolls, they have two options:
#    * Roll straight numbers (7 3 2 == pool 7, hunger 3, diff 2)
#    * Roll using traits (str+dex 3 2)

# In the latter case, we need to figure out which character they are rolling for.
# If they only have one character, then we will allow them to omit the character
# name; however, if they have more than one, they _MUST_ supply a name. Complicating
# this is the fact they could theoretically supply a name despite not using a
# trait-based roll, so we need to check for the character in either case.

import re
from collections import namedtuple

import discord
from discord_ui import Button

from .roll import roll
from .dicemoji import Dicemoji
from . import reroll
from ..common import display_error
from ..databases import CharacterNotFoundError, AmbiguousTraitError, TraitNotFoundError
from ..constants import character_db, DAMAGE

__DICEMOJI = None
__UNIVERSAL_TRAITS = ["willpower", "hunger", "humanity"]
RollParameters = namedtuple("RollParameters", ["pool", "hunger", "difficulty"])

async def parse(ctx, args: str):
    """Parse the user's arguments and attempt to roll the dice."""
    global __DICEMOJI
    if __DICEMOJI is None:
        __DICEMOJI = Dicemoji(ctx.bot)

    # Comments appear after the first # in a command
    comment = None
    if "#" in args:
        args, comment = args.split("#", 1)
        comment = comment.strip()

    args = args.split()
    args = list(args) # To allow for item deletion

    # Determine the character being used, if any
    character_name = None
    character = None
    try:
        character_name, character = character_db.character(
            ctx.guild.id,
            ctx.author.id,
            args[0]
        )
    except CharacterNotFoundError:
        pass

    if character_name is not None:
        del args[0]

        # Yell at the user if they only gave a character name and no roll syntax
        if len(args) == 0:
            await ctx.reply("You need to tell me what to roll!")
            return
    elif character_db.character_count(ctx.guild.id, ctx.author.id) == 1:
        # If the user has one character, they are automatically assumed to be
        # using it even if they don't explicitly supply the name

        # It's only necessary, however, if they're calling traits
        if re.match(r"[A-z_]", " ".join(args)):
            user_characters = character_db.characters(ctx.guild.id, ctx.author.id)

            character_name = list(user_characters.keys())[0]
            character = list(user_characters.values())[0]

    # Attempt to parse the user's roll syntax
    try:
        roll_params = __evaluate_syntax(ctx.guild.id, ctx.author.id, character, *args)
        results = roll(roll_params)
        await __send_results(ctx, character_name, results, comment)

    except (SyntaxError, ValueError) as err:
        await display_error(ctx, character_name or ctx.author.display_name, str(err))


async def __send_results(ctx, character_name, results, comment, rerolled=False):
    character_name = character_name or ctx.author.display_name
    normalmoji = __DICEMOJI.emoji_string(results.normal.dice, False)
    hungermoji = __DICEMOJI.emoji_string(results.hunger.dice, True)

    emoji_string = f"{normalmoji} {hungermoji}"

    embed = discord.Embed(
        title=f"{results.main_takeaway} ({results.total_successes} vs {results.difficulty})",
        description=f"**Margin: {results.margin}**",
        colour=results.embed_color
    )

    # Author line
    author_field = character_name + ("'s Reroll" if rerolled else "'s Roll")
    if results.descriptor is not None:
        author_field += f" ({results.descriptor})"

    embed.set_author(
        name=author_field,
        icon_url=ctx.author.avatar_url
    )

    # Disclosure fields
    embed.add_field(name="Pool", value=str(results.pool))
    embed.add_field(name="Hunger", value=str(results.hunger.count))

    # Comment
    if comment is not None:
        embed.set_footer(text=comment)

    # Calculate re-roll options and display
    reroll_buttons = __generate_reroll_buttons(results)
    if len(reroll_buttons) == 0 or rerolled:
        await ctx.reply(content=emoji_string, embed=embed)
    else:
        msg = await ctx.reply(content=emoji_string, embed=embed, components=reroll_buttons)
        rerolled_results = await reroll.wait_for_reroll(ctx, msg, results)
        await __send_results(ctx, character_name, rerolled_results, comment, rerolled=True)


def __evaluate_syntax(guildid: int, userid: int, character: int, *args):
    """
    Convert the user's syntax to the standardized format: pool, hunger, diff.
    Args:
        guildid (int): The guild's Discord ID
        userid (int): The user's Discord ID
        character (int) (optional): The character's database ID
        args (list): The user's syntax

    Valid syntax: snake_case_words, integers, plus, minus.
    This function does not test if the given traits are in the database!

    Raises ValueError if there is trouble querying the database.
    """
    stack = __substitute_traits(guildid, userid, character, *args)
    return __combine_operators(*stack)


def __substitute_traits(guildid: int, userid: int, character: int, *args):
    """
    Convert the roll syntax into a stack while simultaneously replacing database
    calls with the appropriate values.

    Valid syntax: snake_case_words, integers, plus, minus.

    Raises ValueError if there is trouble querying the database.
    """

    # Split the syntax into words and numbers. Pool elements require math operators
    # between them. Optional: If the final two lack operators, they are considered hunger
    # and difficulty.

    # Pass 1: Normalize
    temp_stack = []

    pattern = re.compile(r"^[\w\d\s\+-]+$")

    for argument in args:
        if not pattern.match(argument):
            raise ValueError("Invalid syntax.")

        # Put spaces around the operators so that we can use split()
        argument = argument.replace("+", " + ")
        argument = argument.replace("-", " - ")

        elements = argument.split()
        temp_stack.extend(elements)

    # Pass 2: Replace database calls with the appropriate values
    final_stack = []

    for item in temp_stack:
        if item in ["+", "-"] or item.isdigit():
            final_stack.append(item)
            continue

        # User is invoking a trait
        if character is None:
            raise ValueError(f"You must supply a character name to use {item}.")

        try:
            rating = character_db.trait_rating(guildid, userid, character, item)
            final_stack.append(rating)
        except TraitNotFoundError as err:
            # We allow universal traits
            match = __match_universal_trait(item)
            if match:
                rating = __get_universal_trait(guildid, userid, character, match)
                final_stack.append(rating)
            else:
                raise ValueError(str(err)) # pylint: disable=raise-missing-from

        except AmbiguousTraitError as err:
            raise ValueError(err.message) # pylint: disable=raise-missing-from

    return final_stack


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

    return RollParameters(*compact_stack)


def __get_universal_trait(guildid: int, userid: int, charid: int, trait):
    """Retrieve a universal trait (Hunger, Willpower, Humanity)."""
    value = getattr(character_db, f"get_{trait}")(guildid, userid, charid)

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
        raise ValueError(str(AmbiguousTraitError(match, matches))) # Cast to avoid messy try blocks

    if len(matches) == 1:
        return matches[0]

    return None


def __generate_reroll_buttons(roll_result) -> list:
    """Generate the buttons for Willpower re-rolls."""
    buttons = []

    if roll_result.can_reroll_failures:
        buttons.append(Button("reroll_failures", "Re-Roll Failures"))

    if roll_result.can_maximize_criticals:
        buttons.append(Button("maximize_criticals", "Maximize Criticals"))

    if roll_result.can_avoid_messy_critical:
        buttons.append(Button("avoid_messy", "Avoid Messy Critical"))

    return buttons
