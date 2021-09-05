"""traits/delete.py - Delete character traits."""

import discord

from .. import common
from .. import constants

async def parse(ctx, *args):
    """Delete character traits. Core attributes and abilities are set to 0."""
    char_name, char_id = common.get_character(ctx.guild.id, ctx.author.id, *args)

    try:
        if char_name is None:
            raise ValueError("You have no characters.")

        args = list(args)
        if char_name.lower() == args[0].lower():
            del args[0]

        if len(args) == 0:
            raise SyntaxError("You must supply a list of traits to delete.")

        __validate_traits(ctx.guild.id, ctx.author.id, char_id, *args)
        __delete_traits(ctx.guild.id, ctx.author.id, char_id, *args)

        embed = discord.Embed(
            title="Traits Removed",
            description=", ".join(args)
        )
        embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="Use //traits list to see remaining traits.")

        await ctx.reply(embed=embed)



    except (ValueError, SyntaxError) as err:
        await common.display_error(ctx, char_name, err)


def __validate_traits(guildid: int, userid: int, charid: int, *traits):
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
        if not constants.character_db.trait_exists(guildid, userid, charid, trait):
            raise ValueError(f"You do not have a trait named `{trait}`.")


def __delete_traits(guildid: int, userid: int, charid: int, *traits):
    """Delete the validated traits."""
    for trait in traits:
        if trait.lower() in constants.SKILLS_AND_ATTRIBUTES:
            # Set attributes and skills to 0 for better UX
            constants.character_db.add_trait(guildid, userid, charid, trait, 0)
        else:
            constants.character_db.delete_trait(guildid, userid, charid, trait)
