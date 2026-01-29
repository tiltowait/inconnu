"""traits/add.py - Add traits to a character."""

import asyncio
import re
from types import SimpleNamespace

import inconnu
import services
import ui
from inconnu.traits.parser import parse_traits
from inconnu.utils.text import pluralize
from models import VChar
from models.vchardocs import VCharTrait
from services import haven

__HELP_URL = {
    False: "https://docs.inconnu.app/command-reference/traits/adding-traits",
    True: "https://docs.inconnu.app/command-reference/traits/updating-traits",
}
__HELP_ADD = "https://docs.inconnu.app/command-reference/traits/adding-traits"
__HELP_UPDATE = "https://docs.inconnu.app/command-reference/traits/updating-traits"


@haven(__HELP_ADD)
async def add(ctx, character: VChar, traits: str, disciplines=False):
    """Add traits to a character. Wrapper for add_update."""
    await __parse(ctx, False, traits, character, disciplines)


@haven(__HELP_UPDATE)
async def update(ctx, character: VChar, traits: str, disciplines=False):
    """Update a character's traits. Wrapper for add_update."""
    await __parse(ctx, True, traits, character, disciplines)


async def __parse(ctx, allow_overwrite: bool, traits: str, character: VChar, disciplines: bool):
    """Add traits to a character."""
    try:
        # Allow the user to input "trait rating", not only "trait=rating"
        traits = re.sub(r"\s*=\s*", r"=", traits)
        traits = re.sub(r"([A-Za-z_])\s+(\d)", r"\g<1>=\g<2>", traits)
        traits_list = traits.split()

        traits_dict = parse_traits(*traits_list, disciplines=disciplines)
        outcome = await __handle_traits(character, traits_dict, allow_overwrite, disciplines)

        await __display_results(ctx, outcome, character, disciplines)

    except (ValueError, SyntaxError) as err:
        await ui.embeds.error(ctx, err, character=character, help=__HELP_URL[allow_overwrite])


async def __handle_traits(character: VChar, traits: dict, overwriting: bool, disciplines: bool):
    """
    Add the rated traits to the character directly.
    Args:
        character (VChar): The character's database ID
        traits (dict): The {str: Optional[int]} dict of traits
        overwriting (bool): Whether we allow overwrites
        disciplines (bool): Whether to class the traits as Disciplines
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

    if disciplines:
        category = VCharTrait.Type.DISCIPLINE
    else:
        category = VCharTrait.Type.CUSTOM

    track_adjustment, assigned = character.assign_traits(to_assign, category)
    assigned = [f"{trait}: `{rating}`" for trait, rating in assigned.items()]
    await character.save()

    return SimpleNamespace(
        assigned=assigned,
        unassigned=unassigned,
        errors=error_traits,
        updating=overwriting,
        track_adjustment=track_adjustment,
    )


def __partition_traits(character, traits):
    """Partition the list of traits into owned and unowned groups."""
    owned = {}
    unowned = {}

    for trait, rating in traits.items():
        if character.has_trait(trait):
            owned[trait] = rating
        else:
            unowned[trait] = rating

    return SimpleNamespace(owned=owned, unowned=unowned)


async def __display_results(ctx, outcome, character: VChar, disciplines: bool):
    """Display the results of the operation."""
    tasks = [__results_embed(ctx, outcome, character, disciplines)]

    # Message for the update channel
    if outcome.assigned:
        term = "Traits" if not disciplines else "Disciplines"
        msg = f"__{ctx.user.mention} updated {character.name}'s traits:__\n"
        msg += ", ".join(outcome.assigned)

        tasks.append(
            services.character_update(
                ctx=ctx, character=character, title=f"{term} Updated", message=msg, color=0xFF9400
            )
        )

    await asyncio.gather(*tasks)


async def __results_embed(ctx, outcome, character: VChar, disciplines: bool):
    """Display the results of the operation in a nice embed."""
    action_present = "Update" if outcome.updating else "Assign"
    action_past = "Updated" if outcome.updating else "Assigned"

    term_singular = "Trait" if not disciplines else "Discipline"
    term_plural = "Traits" if not disciplines else "Disciplines"

    assigned = len(outcome.assigned)
    unassigned = len(outcome.unassigned)
    errors = len(outcome.errors)

    if not outcome.assigned and not outcome.unassigned and outcome.errors:
        title = f"Unable to {action_present} {term_plural}"
    elif outcome.assigned and not outcome.unassigned:
        title = f"{action_past} " + pluralize(assigned, term_singular)
    elif outcome.assigned and outcome.unassigned:
        title = f"{action_past}: {assigned} | Unassigned: {unassigned + errors}"
    else:
        title = f"Couldn't {action_present} " + pluralize(unassigned + errors, term_singular)

    # No color if no mistakes
    # Black if some mistakes
    # Red if only mistakes
    color = None
    if unassigned + errors:
        color = 0x000000 if assigned else 0xFF0000

    embed = ui.embeds.VCharEmbed(ctx, character, title=title, color=color)
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

    view = ui.views.TraitsView(character, ctx.user)
    await ctx.respond(embed=embed, view=view, ephemeral=True)
