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

import re
from types import SimpleNamespace as SN

import discord
from discord_ui import Button

from ..roll_pool import roll_pool
from . import dicemoji
from . import reroll
from .. import common
from ..log import Log
from .. import stats
from ..constants import DAMAGE, UNIVERSAL_TRAITS
from ..settings import Settings
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

    except (SyntaxError, ValueError) as err:
        charid = character.id if character is not None else None
        Log.log("roll_error", user=ctx.author.id, charid=charid, syntax=raw_syntax)

        await common.present_error(
            ctx,
            err,
            ("Input", f"/vr syntax:`{raw_syntax}`"),
            author=owner,
            character=character,
            help_url=__HELP_URL,
            hidden=False
        )


async def display_outcome(ctx, player, character: VChar, results, comment, rerolled=False):
    """Display the roll results."""
    # Log the roll. Doing it here captures normal rolls, re-rolls, and macros
    if ctx.guild is not None:
        stats.Stats.log_roll(ctx.guild.id, player.id, character, results, comment)
    else:
        stats.Stats.log_roll(None, player.id, character, results, comment)

    if Settings.accessible(ctx.author):
        await __outcome_text(ctx, player, character, results, comment, rerolled)
    else:
        await __outcome_embed(ctx, player, character, results, comment, rerolled)


async def __outcome_text(ctx, player, character: VChar, results, comment, rerolled=False):
    """Display the roll results in a nice embed."""
    # Determine the name for the "author" field
    if character is not None:
        title = character.name
    else:
        title = player.display_name

    title += "'s reroll" if rerolled else "'s roll"
    if results.difficulty > 0:
        title += f" vs diff. {results.difficulty}"
    if results.descriptor is not None:
        title += f" ({results.descriptor})"

    contents = [f"```{title}```"]

    takeaway = results.main_takeaway
    if not results.is_total_failure and not results.is_bestial:
        takeaway += f" ({results.total_successes})"

    contents.append(takeaway)
    contents.append(f"Margin: `{results.margin}`")
    contents.append(f"Normal: `{', '.join(map(str, results.normal.dice))}`")
    if len(results.hunger.dice) > 0:
        contents.append(f"Hunger: `{', '.join(map(str, results.hunger.dice))}`")

    if results.pool_str is not None:
        contents.append(f"Pool: `{results.pool_str}`")

    # Comment
    if character is not None:
        impairment = character.impairment
        if impairment is not None:
            if comment is not None:
                if impairment not in comment:
                    comment += f"\n{impairment}"
            else:
                comment = impairment

    if comment is not None:
        contents.append(f"```{comment}```")

    contents = "\n".join(contents)

    # Calculate re-roll options and display
    surging = __determine_surging(character, comment, results.pool_str)
    reroll_buttons = __generate_reroll_buttons(results, surging)
    if rerolled:
        await reroll.present_reroll(ctx, contents, character, player)
    elif len(reroll_buttons) == 0:
        msg = await ctx.respond(contents)
    else:
        msg = await ctx.respond(contents, components=reroll_buttons)
        interaction, rerolled_results = await reroll.wait_for_reroll(ctx, character, msg, results)

        if rerolled_results is not None:
            await display_outcome(interaction, player, character, rerolled_results, comment,
                rerolled=True
            )


async def __outcome_embed(ctx, player, character: VChar, results, comment, rerolled=False):
    """Display the roll results in a nice embed."""
    # Determine the name for the "author" field
    if character is not None:
        character_name = character.name
    else:
        character_name = player.display_name

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

    if character is not None:
        icon = player.display_avatar if character.is_pc else (ctx.guild.icon or "")
    else:
        icon = player.display_avatar

    embed.set_author(
        name=author_field,
        icon_url=icon
    )

    # Disclosure fields
    if results.dice_count < 35:
        normalmoji = dicemoji.emojify(results.normal.dice, False)
        hungermoji = dicemoji.emojify(results.hunger.dice, True)
        embed.add_field(
            name=f"Margin: {results.margin}",
            value=f"{normalmoji} {hungermoji}",
            inline=False
        )
    else:
        lines = []
        if results.normal.count > 0:
            dice = sorted(results.normal.dice, reverse=True)
            lines.append("**Normal Dice:** " + ", ".join(map(str, dice)))
        if results.hunger.count > 0:
            dice = sorted(results.hunger.dice, reverse=True)
            lines.append("**Hunger Dice:** " + ", ".join(map(str, dice)))

        embed.add_field(
            name=f"Margin: {results.margin}",
            value="\n".join(lines),
            inline=False
        )

    embed.add_field(name="Pool", value=str(results.pool))
    embed.add_field(name="Hunger", value=str(results.hunger.count))
    embed.add_field(name="Difficulty", value=str(results.difficulty))

    if results.pool_str is not None:
        embed.add_field(name="Pool", value=results.pool_str)

    # Comment
    if character is not None:
        impairment = character.impairment
        if impairment is not None:
            if comment is not None:
                if impairment not in comment:
                    comment += f"\n{impairment}"
            else:
                comment = impairment

    if comment is not None:
        embed.set_footer(text=comment)

    # Calculate re-roll options and display
    surging = __determine_surging(character, comment, results.pool_str)
    reroll_buttons = __generate_reroll_buttons(results, surging)

    if rerolled:
        await reroll.present_reroll(ctx, embed, character, player)
    elif len(reroll_buttons) == 0:
        msg = await ctx.respond(embed=embed)
    else:
        msg = await ctx.respond(embed=embed, components=reroll_buttons)
        interaction, rerolled_results = await reroll.wait_for_reroll(ctx, character, msg, results)

        if rerolled_results is not None:
            await display_outcome(interaction, player, character, rerolled_results, comment,
                rerolled=True
            )


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
                trait_stack.append(match.title())
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


def __determine_surging(character, comment, pool) -> bool:
    """Determine whether to show the surge button."""
    if character is None or character.splat == "mortal":
        return False

    combined = f"{comment} {pool}"
    match = re.match(r"^.*(\s+surge|surge\s+.*|surge)$", combined, re.IGNORECASE)
    return match is not None


def __generate_reroll_buttons(roll_result, surging: bool) -> list:
    """Generate the buttons for Willpower re-rolls."""
    buttons = []

    if roll_result.can_reroll_failures:
        buttons.append(Button("Re-Roll Failures", "reroll_failures"))

    if roll_result.can_maximize_criticals:
        buttons.append(Button("Maximize Crits", "maximize_criticals"))

    if roll_result.can_avoid_messy_critical:
        buttons.append(Button("Avoid Messy", "avoid_messy"))

    if roll_result.can_risky_messy_critical:
        buttons.append(Button("Risky Avoid Messy", "risky"))

    if surging:
        buttons.append(Button("Rouse for Surge", "surge", "red"))

    return buttons


def needs_character(syntax: str):
    """Determines whether a roll needs a character."""
    return re.search(r"[A-z_]", syntax) is not None
