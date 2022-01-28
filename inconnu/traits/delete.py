"""traits/delete.py - Delete character traits."""

from types import SimpleNamespace

import discord

from . import traitcommon
from .. import common
from .. import constants
from ..settings import Settings
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/trait-management?id=deleting-traits"


async def delete(ctx, traits: str, character=None):
    """Delete character traits. Core attributes and abilities are set to 0."""
    try:
        tip = f"`/traits delete` `traits:{traits}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)
        traits = traits.split()

        if len(traits) == 0:
            # Shouldn't be possible to reach here, but just in case Discord messes up
            raise SyntaxError("You must supply a list of traits to delete.")

        traitcommon.validate_trait_names(*traits)
        outcome = __delete_traits(character, *traits)

        if Settings.accessible(ctx.user):
            await __outcome_text(ctx, character, outcome)
        else:
            await __outcome_embed(ctx, character, outcome)

    except (ValueError, SyntaxError) as err:
        await common.present_error(ctx, err, character=character, help_url=__HELP_URL)
    except common.FetchError:
        pass


async def __outcome_text(ctx, character, outcome):
    """Display the outcome in plain text."""
    contents = [character.name + "\n"]

    if len(outcome.deleted) > 0:
        deleted = ", ".join(map(lambda trait: f"`{trait}`", outcome.deleted))
        contents.append(f"Deleted {deleted}.")

    if len(outcome.errors) > 0:
        errs = ", ".join(map(lambda error: f"`{error}`", outcome.errors))
        contents.append(f"These traits don't exist: {errs}.")

    await ctx.respond("\n".join(contents), ephemeral=True)


async def __outcome_embed(ctx, character, outcome):
    """Display the operation outcome in an embed."""
    embed = discord.Embed(
        title="Trait Removal"
    )
    embed.set_author(name=character.name, icon_url=ctx.user.display_avatar)
    embed.set_footer(text="To see remaining traits: /traits list")

    if len(outcome.deleted) > 0:
        deleted = ", ".join(map(lambda trait: f"`{trait}`", outcome.deleted))
        embed.add_field(name="Deleted", value=deleted)

    if len(outcome.errors) > 0:
        errs = ", ".join(map(lambda error: f"`{error}`", outcome.errors))
        embed.add_field(name="Do not exist", value=errs, inline=False)

    await ctx.respond(embed=embed, ephemeral=True)


def __delete_traits(character: VChar, *traits) -> list:
    """
    Delete the validated traits. If the trait is a core trait, then it is set to 0.
    Returns (list): A list of traits that could not be found.
    """
    deleted = []
    errs = []
    for trait in traits:
        if trait.lower() in constants.SKILLS_AND_ATTRIBUTES:
            # Set attributes and skills to 0 for better UX
            character.update_trait(trait, 0)
        else:
            try:
                character.delete_trait(trait)
                deleted.append(trait)
            except errors.TraitNotFoundError:
                errs.append(trait)

    return SimpleNamespace(deleted=deleted, errors=errs)
