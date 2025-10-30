"""traits/delete.py - Delete character traits."""

from types import SimpleNamespace
from typing import TYPE_CHECKING

import inconnu
from inconnu.traits import traitcommon
from inconnu.utils.haven import haven

if TYPE_CHECKING:
    from inconnu.models import VChar

__HELP_URL = "https://docs.inconnu.app/command-reference/traits/removing-traits"


@haven(__HELP_URL)
async def delete(ctx, character, traits: str, disciplines=False):
    """Delete character traits. Core attributes and abilities are set to 0."""
    try:
        traits = traits.split()
        if not traits:
            # Shouldn't be possible to reach here, but just in case Discord messes up
            raise SyntaxError("You must supply a list of traits or disciplines to delete.")

        traitcommon.validate_trait_names(*traits, disciplines=disciplines)
        outcome = __delete_traits(character, *traits)
        await __outcome_embed(ctx, character, outcome, disciplines)
        await character.commit()

    except (ValueError, SyntaxError) as err:
        await inconnu.embeds.error(ctx, err, character=character, help=__HELP_URL)


async def __outcome_embed(ctx, character, outcome, disciplines: bool):
    """Display the operation outcome in an embed."""
    term = "Trait" if not disciplines else "Discipline"

    embed = inconnu.embeds.VCharEmbed(ctx, character, title=f"{term} Removal")
    embed.set_footer(text="To see remaining traits: /traits list")

    if outcome.deleted:
        deleted = ", ".join(map(lambda trait: f"`{trait}`", outcome.deleted))
        embed.add_field(name="Removed", value=deleted)
        embed.color = None

    if outcome.errors:
        errs = ", ".join(map(lambda error: f"`{error}`", outcome.errors))
        embed.add_field(name="Do not exist", value=errs, inline=False)
        embed.color = 0x000000 if outcome.deleted else 0xFF0000

    view = inconnu.views.TraitsView(character, ctx.user)
    await ctx.respond(embed=embed, view=view, ephemeral=True)


def __delete_traits(character: "VChar", *traits) -> list:
    """
    Delete the validated traits. If the trait is a core trait, then it is set to 0.
    Returns (list): A list of traits that could not be found.
    """
    deleted = []
    errs = []
    standard_traits = map(lambda t: t.lower(), inconnu.constants.get_standard_traits())

    for trait in traits:
        if trait.lower() in standard_traits:
            # Set attributes and skills to 0 for better UX
            _, trait = character.assign_traits({trait: 0})
            deleted.extend(trait.keys())
        else:
            try:
                trait = character.delete_trait(trait)
                deleted.append(trait)
            except inconnu.errors.TraitNotFound:
                errs.append(trait)

    return SimpleNamespace(deleted=deleted, errors=errs)
