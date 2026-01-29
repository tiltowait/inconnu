"""traits/delete.py - Delete character traits."""

from typing import NamedTuple

from discord import ApplicationContext, Interaction

import errors
import inconnu
import ui
from inconnu.traits import traitcommon
from models import VChar
from services import haven

__HELP_URL = "https://docs.inconnu.app/command-reference/traits/removing-traits"


class DeletionResult(NamedTuple):
    """Contains the list of deleted traits and traits not found."""

    deleted: list[str]
    errors: list[str]


@haven(__HELP_URL)
async def delete(
    ctx: Interaction | ApplicationContext, character, traits_input: str, disciplines=False
):
    """Delete character traits. Core attributes and abilities are set to 0."""
    try:
        traits = traits_input.split()
        if not traits:
            # Shouldn't be possible to reach here, but just in case Discord messes up
            raise SyntaxError("You must supply a list of traits or disciplines to delete.")

        traitcommon.validate_trait_names(*traits, disciplines=disciplines)
        outcome = __delete_traits(character, *traits)
        await __outcome_embed(ctx, character, outcome, disciplines)
        await character.save()

    except (ValueError, SyntaxError) as err:
        await ui.embeds.error(ctx, err, character=character, help=__HELP_URL)


async def __outcome_embed(
    ctx: Interaction | ApplicationContext, character, outcome, disciplines: bool
):
    """Display the operation outcome in an embed."""
    term = "Trait" if not disciplines else "Discipline"

    embed = ui.embeds.VCharEmbed(ctx, character, title=f"{term} Removal")
    embed.set_footer(text="To see remaining traits: /traits list")

    if outcome.deleted:
        deleted = ", ".join(map(lambda trait: f"`{trait}`", outcome.deleted))
        embed.add_field(name="Removed", value=deleted)
        embed.color = None

    if outcome.errors:
        errs = ", ".join(map(lambda error: f"`{error}`", outcome.errors))
        embed.add_field(name="Do not exist", value=errs, inline=False)
        embed.color = 0x000000 if outcome.deleted else 0xFF0000

    view = ui.views.TraitsView(character, ctx.user)
    await ctx.respond(embed=embed, view=view, ephemeral=True)


def __delete_traits(character: VChar, *traits: str) -> DeletionResult:
    """
    Delete the validated traits. If the trait is a core trait, then it is set to 0.
    Returns (list): A list of traits that could not be found.
    """
    deleted = []
    errs = []
    standard_traits = map(lambda t: t.lower(), inconnu.constants.get_standard_traits())

    for trait_name in traits:
        if trait_name.lower() in standard_traits:
            # Set attributes and skills to 0 for better UX
            _, trait = character.assign_traits({trait_name: 0})
            deleted.extend(trait.keys())
        else:
            try:
                trait = character.delete_trait(trait_name)
                deleted.append(trait)
            except errors.TraitNotFound:
                errs.append(trait_name)

    return DeletionResult(deleted=deleted, errors=errs)
