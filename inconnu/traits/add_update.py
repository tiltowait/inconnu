"""traits/add.py - Add traits to a character."""

import asyncio
import re
from types import SimpleNamespace

import discord

import inconnu.settings
import inconnu.views

from .. import common
from ..vchar import VChar
from .parser import parse_traits

__HELP_URL = {
    False: "https://www.inconnu.app/#/trait-management?id=adding-traits",
    True: "https://www.inconnu.app/#/trait-management?id=updating-traits",
}


async def add(ctx, traits: str, character: str, specialties=False):
    """Add traits to a character. Wrapper for add_update."""
    await __parse(ctx, False, traits, character, specialties)


async def update(ctx, traits: str, character: str):
    """Update a character's traits. Wrapper for add_update."""
    await __parse(ctx, True, traits, character)


async def __parse(ctx, allow_overwrite: bool, raw_traits: str, character: str, specialties=False):
    """Add traits to a character."""
    try:
        traits = raw_traits

        key = "update" if allow_overwrite else "add"
        term = "traits" if not specialties else "specialties"

        # Specialties are just 1-point traits, but when entered, they don't
        # have an assigned value. Let's do that now.
        if specialties:
            if "=" in traits:
                # They did a regular trait assignment
                raise ValueError(
                    f"Specialties can't have assigned values. Use `/traits {key}` instead."
                )

            traits = map(lambda s: f"{s}=1", traits.split())
        else:
            # Allow the user to input "trait rating", not only "trait=rating"
            traits = re.sub(r"\s*=\s*", r"=", traits)
            traits = re.sub(r"([A-Za-z_])\s+(\d)", r"\g<1>=\g<2>", traits)
            traits = traits.split()

        traits = parse_traits(*traits, specialties=specialties)

        haven = inconnu.utils.Haven(
            ctx,
            character=character,
            tip=f"`/{term} {key}` `{term}:{raw_traits}` `character:CHARACTER`",
            help=__HELP_URL[allow_overwrite],
        )
        character = await haven.fetch()
        outcome = await __handle_traits(character, traits, allow_overwrite)

        await __display_results(ctx, outcome, character, specialties)

    except (ValueError, SyntaxError) as err:
        await inconnu.utils.error(ctx, err, character=character, help=__HELP_URL[allow_overwrite])


async def __handle_traits(character: VChar, traits: dict, overwriting: bool):
    """
    Add the rated traits to the character directly.
    Args:
        character (VChar): The character's database ID
        traits (dict): The {str: Optional[int]} dict of traits
        overwriting (bool): Whether we allow overwrites
    All traits and ratings are assumed to be valid at this time.
    """
    partition = __partition_traits(character, traits)

    if overwriting:
        error_traits = list(partition.unowned.keys())
        unassigned = [k for k, v in partition.owned.items() if v is None]
        to_assign = {k: v for k, v in partition.owned.items() if v is not None}
    else:
        error_traits = list(partition.owned.keys())
        unassigned = [k for k, v in partition.unowned.items() if v is None]
        to_assign = {k: v for k, v in partition.unowned.items() if v is not None}

    track_adjustment, assigned = await character.assign_traits(to_assign)
    assigned = [f"{trait}: `{rating}`" for trait, rating in assigned.items()]

    return SimpleNamespace(
        assigned=assigned,
        unassigned=unassigned,
        errors=error_traits,
        updating=overwriting,
        track_adjustment=track_adjustment,
    )


def __partition_traits(character, traits):
    """Partition the list of traits into owned and unowned groups."""
    my_traits = character.traits
    owned = {}
    unowned = {}

    for trait, rating in traits.items():
        if trait.lower() in map(lambda t: t.lower(), my_traits.keys()):
            owned[trait] = rating
        else:
            unowned[trait] = rating

    return SimpleNamespace(owned=owned, unowned=unowned)


async def __display_results(ctx, outcome, character: VChar, specialties: bool):
    """Display the results of the operation."""
    tasks = [__results_embed(ctx, outcome, character, specialties)]

    # Message for the update channel
    if outcome.assigned:
        term = "Traits" if not specialties else "Specialties"
        msg = f"__{ctx.user.mention} updated {character.name}'s traits:__\n"
        msg += ", ".join(outcome.assigned)

        tasks.append(
            inconnu.common.report_update(
                ctx=ctx, character=character, title=f"{term} Updated", message=msg, color=0xFF9400
            )
        )

    await asyncio.gather(*tasks)


async def __results_embed(ctx, outcome, character: VChar, specialties: bool):
    """Display the results of the operation in a nice embed."""
    action_present = "Update" if outcome.updating else "Assign"
    action_past = "Updated" if outcome.updating else "Assigned"

    term_singular = "Trait" if not specialties else "Specialty"
    term_plural = "Traits" if not specialties else "Specialties"

    assigned = len(outcome.assigned)
    unassigned = len(outcome.unassigned)
    errors = len(outcome.errors)

    if not outcome.assigned and not outcome.unassigned and outcome.errors:
        title = f"Unable to {action_present} {term_plural}"
    elif outcome.assigned and not outcome.unassigned:
        title = f"{action_past} " + common.pluralize(assigned, term_singular)
    elif outcome.assigned and outcome.unassigned:
        title = f"{action_past}: {assigned} | Unassigned: {unassigned + errors}"
    else:
        title = f"Couldn't {action_present} " + common.pluralize(unassigned + errors, term_singular)

    # No color if no mistakes
    # Black if some mistakes
    # Red if only mistakes
    color = discord.Embed.Empty
    if unassigned + errors:
        color = 0x000000 if assigned else 0xFF0000

    embed = discord.Embed(title=title, color=color)
    embed.set_author(name=character.name, icon_url=inconnu.get_avatar(ctx.user))
    embed.set_footer(text=outcome.track_adjustment)

    if outcome.assigned:
        assigned = "\n".join(outcome.assigned)
        embed.add_field(name=action_past, value=assigned)

    if outcome.unassigned:
        unassigned = ", ".join(list(map(lambda trait: f"`{trait}`", outcome.unassigned)))
        embed.add_field(name="No value given", value=unassigned)

    if outcome.errors:
        errs = ", ".join(list(map(lambda trait: f"`{trait}`", outcome.errors)))
        if outcome.updating:
            field_name = "Error! You don't have these traits"
            embed.set_footer(text="To add a trait, use /traits add")
        else:
            field_name = "Error! You already have these traits"
            embed.set_footer(text="To update a trait, use /traits update")
        embed.add_field(name=field_name, value=errs, inline=False)

    view = inconnu.views.TraitsView(character, ctx.user)
    await ctx.respond(embed=embed, view=view, ephemeral=True)


async def __results_text(ctx, outcome, character: VChar):
    """Display the results in plain text."""
    contents = [f"**{character.name}: Trait Assignment**\n"]

    if outcome.assigned:
        assigned = ", ".join(outcome.assigned)
        action = "Updated" if outcome.updating else "Assigned"
        contents.append(f"**{action}:** {assigned}")

    if outcome.unassigned:
        unassigned = ", ".join(map(lambda trait: f"`{trait}`", outcome.unassigned))
        contents.append(f"**No value given:** {unassigned}")

    if outcome.errors:
        errs = ", ".join(map(lambda trait: f"`{trait}`", outcome.errors))
        if outcome.updating:
            err_field = "**Error!** You don't have " + errs
        else:
            err_field = "**Error!** You already have " + errs
        contents.append(err_field)

    contents.append(f"```{outcome.track_adjustment}```")

    view = inconnu.views.TraitsView(character, ctx.user)
    await ctx.respond("\n".join(contents), view=view, ephemeral=True)
