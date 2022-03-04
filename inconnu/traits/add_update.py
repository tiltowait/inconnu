"""traits/add.py - Add traits to a character."""

import re
from types import SimpleNamespace

import discord

import inconnu.settings
from .parser import parse_traits
from .. import common
from ..vchar import VChar

__HELP_URL = {
    False: "https://www.inconnu-bot.com/#/trait-management?id=adding-traits",
    True: "https://www.inconnu-bot.com/#/trait-management?id=updating-traits"
}


async def add(ctx, traits: str, character: str):
    """Add traits to a character. Wrapper for add_update."""
    await __parse(ctx, False, traits, character)


async def update(ctx, traits: str, character: str):
    """Update a character's traits. Wrapper for add_update."""
    await __parse(ctx, True, traits, character)


async def __parse(ctx, allow_overwrite: bool, traits: str, character: str):
    """Add traits to a character."""
    try:
        key = "update" if allow_overwrite else "add"
        tip = f"`/traits {key}` `traits:{traits}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL[allow_overwrite])

        # Allow the user to input "trait rating", not only "trait=rating"
        traits = re.sub(r"\s*=\s*", r"=", traits)
        traits = re.sub(r"([A-Za-z_])\s+(\d)", r"\g<1>=\g<2>", traits)

        traits = parse_traits(*traits.split())
        outcome = await __handle_traits(character, traits, allow_overwrite)

        await __display_results(ctx, outcome, character.name)

    except (ValueError, SyntaxError) as err:
        await common.present_error(
            ctx,
            err,
            character=character,
            help_url=__HELP_URL[allow_overwrite]
        )
    except common.FetchError:
        pass


async def __handle_traits(character: VChar, traits: dict, overwriting: bool):
    """
    Add the rated traits to the character directly.
    Args:
        character (VChar): The character's database ID
        traits (dict): The {str: Optional[int]} dict of traits
        overwriting (bool): Whether we allow overwrites
    All traits and ratings are assumed to be valid at this time.
    """
    partition = character.owned_traits(**traits)

    if overwriting:
        error_traits = list(partition.unowned.keys())
        unassigned = [k for k, v in partition.owned.items() if v is None]
        to_assign = {k: v for k, v in partition.owned.items() if v is not None}
    else:
        error_traits = list(partition.owned.keys())
        unassigned = [k for k, v in partition.unowned.items() if v is None]
        to_assign = {k: v for k, v in partition.unowned.items() if v is not None}

    assigned = await character.assign_traits(to_assign)
    assigned = [f"{trait}: `{rating}`" for trait, rating in assigned.items()]

    return SimpleNamespace(
        assigned=assigned,
        unassigned=unassigned,
        errors=error_traits,
        updating=overwriting
    )


async def __display_results(ctx, outcome, char_name: str):
    """Display the results of the operation."""
    if await inconnu.settings.accessible(ctx.user):
        await __results_text(ctx, outcome, char_name)
    else:
        await __results_embed(ctx, outcome, char_name)


async def __results_embed(ctx, outcome, char_name: str):
    """Display the results of the operation in a nice embed."""
    action_present = "Update" if outcome.updating else "Assign"
    action_past = "Updated" if outcome.updating else "Assigned"

    assigned = len(outcome.assigned)
    unassigned = len(outcome.unassigned)
    errors = len(outcome.errors)

    if not outcome.assigned and not outcome.unassigned and outcome.errors:
        title = f"Unable to {action_present} Traits"
    elif outcome.assigned and not outcome.unassigned:
        title = f"{action_past} {common.pluralize(assigned, 'Trait')}"
    elif outcome.assigned and outcome.unassigned:
        title = f"{action_past}: {assigned} | Unassigned: {unassigned + errors}"
    else:
        title = f"Couldn't {action_present} {common.pluralize(unassigned + errors, 'Trait')}"

    # No color if no mistakes
    # Black if some mistakes
    # Red if only mistakes
    color = discord.Embed.Empty
    if unassigned + errors:
        color = 0x000000 if assigned else 0xff0000

    embed = discord.Embed(
        title=title,
        color=color
    )
    embed.set_author(name=char_name, icon_url=ctx.user.display_avatar)
    if outcome.assigned:
        assigned = "\n".join(outcome.assigned)
        embed.add_field(name=action_past, value=assigned)

    if outcome.unassigned:
        unassigned = ", ".join(list(map(lambda trait: f"`{trait}`", outcome.unassigned)))
        embed.add_field(name="No value given", value=unassigned)
        embed.set_footer(text="Run the command again to give ratings for the unassigned traits.")

    if outcome.errors:
        errs = ", ".join(list(map(lambda trait: f"`{trait}`", outcome.errors)))
        if outcome.updating:
            field_name = "Error! You don't have these traits"
        else:
            field_name = "Error! You already have these traits"
        embed.add_field(name=field_name, value=errs, inline=False)

    await ctx.respond(embed=embed, ephemeral=True)


async def __results_text(ctx, outcome, char_name: str):
    """Display the results in plain text."""
    contents = [f"**{char_name}: Trait Assignment**\n"]

    if outcome.assigned:
        assigned = ", ".join(outcome.assigned)
        action = "Updated" if outcome.updating else "Assigned"
        contents.append(f"**{action}:** {assigned}")

    footer = None
    if outcome.unassigned:
        unassigned = ", ".join(map(lambda trait: f"`{trait}`", outcome.unassigned))
        contents.append(f"**No value given:** {unassigned}")
        footer = "Run the command again to assign ratings to the unassigned traits."

    if outcome.errors:
        errs = ", ".join(map(lambda trait: f"`{trait}`", outcome.errors))
        if outcome.updating:
            err_field = "**Error!** You don't have " + errs
        else:
            err_field = "**Error!** You already have " + errs
        contents.append(err_field)

    if footer is not None:
        contents.append(f"```{footer}```")

    await ctx.respond("\n".join(contents), ephemeral=True)
