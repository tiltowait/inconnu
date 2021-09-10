"""traits/delete.py - Delete character traits."""

import discord

from ..vchar import errors, VChar
from .. import common
from .. import constants

async def parse(ctx, traits: str, character=None):
    """Delete character traits. Core attributes and abilities are set to 0."""
    try:
        character = VChar.strict_find(ctx.guild.id, ctx.author.id, character)
        traits = traits.split()

        if len(traits) == 0:
            # Shouldn't be possible to reach here, but just in case Discord messes up
            raise SyntaxError("You must supply a list of traits to delete.")

        await __validate_traits(character, *traits)
        await __delete_traits(character, *traits)

        embed = discord.Embed(
            title="Traits Removed",
            description=", ".join(map(lambda trait: f"`{trait}`", traits))
        )
        embed.set_author(name=character.name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="To see remaining traits: /traits list")

        await ctx.respond(embed=embed, hidden=True)

    except (ValueError, SyntaxError, errors.CharacterError) as err:
        name = character.name if character is not None else ctx.author.display_name
        await common.display_error(ctx, name, err)


async def __validate_traits(character: VChar, *traits):
    """
    Raises a ValueError if a trait doesn't exist and a SyntaxError
    if the syntax is bad.
    """
    for trait in traits:
        if constants.VALID_DB_KEY_PATTERN.match(trait) is None:
            raise SyntaxError(f"Traits can only have letters and underscores. Received `{trait}`")

        # We check but do not delete traits yet, because we want to delete them all
        # in one go. This is easier on the user, because they can just copy + paste
        # after fixing a typo or what-have-you.
        _ = character.find_trait(trait) # Raised exception will trigger failure


async def __delete_traits(character: VChar, *traits):
    """Delete the validated traits."""
    for trait in traits:
        if trait.lower() in constants.SKILLS_AND_ATTRIBUTES:
            # Set attributes and skills to 0 for better UX
            character.update_trait(trait, 0)
        else:
            character.delete_trait(trait)
