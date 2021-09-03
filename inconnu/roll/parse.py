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

from .roll import roll
from .dicemoji import Dicemoji
from ..databases import CharacterDB, AmbiguousTraitError, TraitNotFoundError

__DATABASE = CharacterDB()
__DICEMOJI = None
RollParameters = namedtuple("RollParameters", ["pool", "hunger", "difficulty"])

async def parse(ctx, *args):
    """Parse the user's arguments and attempt to roll the dice."""

    global __DICEMOJI
    if __DICEMOJI is None:
        __DICEMOJI = Dicemoji(ctx.bot)

    args = list(args) # To allow for item deletion

    # Determine the character being used, if any
    user_characters = __DATABASE.characters(ctx.guild.id, ctx.author.id)
    character_name = None
    character = None

    if args[0] in user_characters:
        character_name = args[0]
        character = user_characters[character_name]
        del args[0]

        # Yell at the user if they only gave a character name and no roll syntax
        if len(args) == 0:
            await ctx.reply("You need to tell me what to roll!")
            return
    elif len(user_characters) == 1:
        # If the user has one character, they are automatically assumed to be
        # using it even if they don't explicitly supply the name

        # It's only necessary, however, if they're calling traits
        if re.match(r"[A-z_]", " ".join(args)):
            character_name = list(user_characters.keys())[0]
            character = list(user_characters.values())[0]

    # Attempt to parse the user's roll syntax
    try:
        stack = __expand_syntax(ctx.guild.id, ctx.author.id, character, *args)
        roll_params = __standardize_syntax(*stack)

        # Build the embed
        results = roll(roll_params)

        author_name = character_name or ctx.author.display_name

        normalmoji = __DICEMOJI.emoji_string(results.normal.dice, False)
        hungermoji = __DICEMOJI.emoji_string(results.hunger.dice, True)

        emoji_string = f"{normalmoji} {hungermoji}"

        embed = discord.Embed(
            title=f"{results.main_takeaway} ({results.total_successes} vs {results.difficulty})",
            description=f"**Margin: {results.margin}**",
            colour=results.embed_color
        )
        embed.set_author(name=f"{author_name}'s roll", icon_url=ctx.author.avatar_url)
        embed.add_field(name="Pool", value=str(results.pool))
        embed.add_field(name="Hunger", value=str(results.hunger.count))

        await ctx.reply(content=emoji_string, embed=embed)

    except ValueError as err:
        await ctx.reply(f"Error: {str(err)}")


def __expand_syntax(guildid: int, userid: int, character: int, *args):
    """
    Check the roll syntax for database calls and replace them with the appropriate
    values.

    Valid syntax: snake_case_words, integers, plus, minus.
    This function does not test if the given traits are in the database!

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
            rating = __DATABASE.trait_rating(guildid, userid, character, item)
            final_stack.append(rating)
        except (TraitNotFoundError, AmbiguousTraitError) as exception:
            raise ValueError(exception.message) #pylint: disable=raise-missing-from

    return final_stack


def __standardize_syntax(*stack):
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
