"""traits/delete.py - Delete character traits."""

import discord

from .. import common
from .. import constants

async def parse(ctx, traits: str, character=None):
    """Delete character traits. Core attributes and abilities are set to 0."""
    char_name = None

    try:
        char_name, char_id = await common.match_character(ctx.guild.id, ctx.author.id, character)

        traits = traits.split()
        if len(traits) == 0:
            # Shouldn't be possible to reach here, but just in case Discord messes up
            raise SyntaxError("You must supply a list of traits to delete.")

        await __validate_traits(char_id, *traits)
        await __delete_traits(char_id, *traits)

        embed = discord.Embed(
            title="Traits Removed",
            description=", ".join(map(lambda trait: f"`{trait}`", traits))
        )
        embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="To see remaining traits: /traits list")

        await ctx.respond(embed=embed, hidden=True)

    except (ValueError, SyntaxError) as err:
        await common.display_error(ctx, char_name or ctx.author.display_name, err)


async def __validate_traits(charid: int, *traits):
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
        if not await constants.character_db.trait_exists(charid, trait):
            raise ValueError(f"You do not have a trait named `{trait}`. No traits removed.")


async def __delete_traits(charid: int, *traits):
    """Delete the validated traits."""
    async with constants.character_db.conn.transaction():
        for trait in traits:
            if trait.lower() in constants.SKILLS_AND_ATTRIBUTES:
                # Set attributes and skills to 0 for better UX
                await constants.character_db.add_trait(charid, trait, 0)
            else:
                await constants.character_db.delete_trait(charid, trait)
