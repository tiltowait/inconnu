"""traits/delete.py - Delete character traits."""

from types import SimpleNamespace

import discord

import inconnu

from ..vchar import VChar, errors
from . import traitcommon

__HELP_URL = "https://www.inconnu.app/#/trait-management?id=deleting-traits"


async def delete(ctx, traits: str, character=None, specialties=False):
    """Delete character traits. Core attributes and abilities are set to 0."""
    try:
        term = "traits" if not specialties else "specialties"
        command = "traits delete" if not specialties else "specialties remove"

        haven = inconnu.utils.Haven(
            ctx,
            character=character,
            tip=f"`/{command}` `{term}:{traits}` `character:CHARACTER`",
            help=__HELP_URL,
        )
        character = await haven.fetch()

        traits = traits.split()
        if not traits:
            # Shouldn't be possible to reach here, but just in case Discord messes up
            raise SyntaxError(f"You must supply a list of {term} to delete.")

        traitcommon.validate_trait_names(*traits, specialties=specialties)
        outcome = await __delete_traits(character, *traits)
        await __outcome_embed(ctx, character, outcome, specialties)

    except (ValueError, SyntaxError) as err:
        await inconnu.utils.error(ctx, err, character=character, help=__HELP_URL)


async def __outcome_embed(ctx, character, outcome, specialties: bool):
    """Display the operation outcome in an embed."""
    term = "Trait" if not specialties else "Specialty"

    embed = discord.Embed(title=f"{term} Removal")
    embed.set_author(name=character.name, icon_url=inconnu.get_avatar(ctx.user))
    embed.set_footer(text="To see remaining traits: /traits list")

    if outcome.deleted:
        deleted = ", ".join(map(lambda trait: f"`{trait}`", outcome.deleted))
        embed.add_field(name="Deleted", value=deleted)
        embed.color = discord.Embed.Empty

    if outcome.errors:
        errs = ", ".join(map(lambda error: f"`{error}`", outcome.errors))
        embed.add_field(name="Do not exist", value=errs, inline=False)
        embed.color = 0x000000 if outcome.deleted else 0xFF0000

    view = inconnu.views.TraitsView(character, ctx.user)
    await ctx.respond(embed=embed, view=view, ephemeral=True)


async def __delete_traits(character: VChar, *traits) -> list:
    """
    Delete the validated traits. If the trait is a core trait, then it is set to 0.
    Returns (list): A list of traits that could not be found.
    """
    deleted = []
    errs = []
    standard_traits = map(lambda t: t.lower(), inconnu.constants.FLAT_TRAITS())

    for trait in traits:
        if trait.lower() in standard_traits:
            # Set attributes and skills to 0 for better UX
            _, trait = await character.assign_traits({trait: 0})
            deleted.extend(trait.keys())
        else:
            try:
                trait = await character.delete_trait(trait)
                deleted.append(trait)
            except errors.TraitNotFoundError:
                errs.append(trait)

    return SimpleNamespace(deleted=deleted, errors=errs)
