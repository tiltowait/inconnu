"""traits/delete.py - Delete character traits."""

from types import SimpleNamespace

import discord

from . import traitcommon
from ..vchar import errors, VChar
from .. import common
from .. import constants

__HELP_URL = "https://www.inconnu-bot.com/#/trait-management?id=deleting-traits"


async def parse(ctx, traits: str, character=None):
    """Delete character traits. Core attributes and abilities are set to 0."""
    try:
        character = VChar.fetch(ctx.guild.id, ctx.author.id, character)

    except errors.UnspecifiedCharacterError as err:
        tip = f"`/traits delete` `traits:{traits}` `character:CHARACTER`"
        character = await common.select_character(ctx, err, __HELP_URL, ("Proper syntax", tip))

        if character is None:
            # They didn't select a character
            return
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err, __HELP_URL)
        return

    try:
        traits = traits.split()

        if len(traits) == 0:
            # Shouldn't be possible to reach here, but just in case Discord messes up
            raise SyntaxError("You must supply a list of traits to delete.")

        traitcommon.validate_trait_names(*traits)
        outcome = __delete_traits(character, *traits)

        embed = discord.Embed(
            title="Trait Removal"
        )
        embed.set_author(name=character.name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="To see remaining traits: /traits list")

        if len(outcome.deleted) > 0:
            deleted = ", ".join(map(lambda trait: f"`{trait}`", outcome.deleted))
            embed.add_field(name="Deleted", value=deleted)

        if len(outcome.errors) > 0:
            errs = ", ".join(map(lambda error: f"`{error}`", outcome.errors))
            embed.add_field(name="Do not exist", value=errs, inline=False)

        await ctx.respond(embed=embed, hidden=True)

    except (ValueError, SyntaxError) as err:
        await common.display_error(ctx, character.name, err, __HELP_URL)


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
