"""traits/add.py - Add traits to a character."""

import discord

from .parser import parse_traits
from .traitwizard import TraitWizard
from .. import common
from ..constants import character_db

async def parse(ctx, allow_overwrite: bool, *args):
    """Add traits to a character."""
    char_name, char_id = common.get_character(ctx.guild.id, ctx.author.id, *args)

    if char_name is None:
        message = common.character_options_message(ctx.guild.id, ctx.author.id, "")
        await ctx.reply(message)
        return

    args = list(args)
    if char_name.lower() == args[0].lower():
        del args[0]

    # Got the character
    try:
        traits = parse_traits(*args)
        assigned_traits, wizard_traits = await __handle_traits(
            ctx.guild.id,
            ctx.author.id,
            char_id,
            traits,
            allow_overwrite
        )

        await __display_results(ctx, assigned_traits, wizard_traits, char_name)

        if len(wizard_traits) > 0:
            wizard = TraitWizard(ctx, char_name, wizard_traits)
            await wizard.begin()

    except (ValueError, SyntaxError) as err:
        await common.display_error(ctx, char_name, err)


async def __handle_traits(guildid: int, userid: int, charid: int, traits: dict, overwriting: bool):
    """
    Add the rated traits to the character directly. Create a wizard for the rest.
    Args:
        guildid (int): The guild's Discord ID
        userid (int): The user's Discord ID
        charid (int): The character's database ID
        traits (dict): The {str: Optional[int]} dict of traits
        overwriting (bool): Whether we allow overwrites
    All traits and ratings are assumed to be valid at this time.
    """
    assigned_traits = []
    wizard_traits = []
    for trait, rating in traits.items():
        if not overwriting and character_db.trait_exists(guildid, userid, charid, trait):
            raise ValueError(f"You already have a trait named `{trait}`.")

        if rating is None:
            wizard_traits.append(trait)
            continue

        character_db.add_trait(guildid, userid, charid, trait, rating)
        assigned_traits.append(trait)

    return (assigned_traits, wizard_traits)


async def __display_results(ctx, assigned: list, unassigned: list, char_name: str):
    """Display the results of the operation in a nice embed."""
    title = None
    if len(unassigned) > 0:
        title = "Entering Incognito Mode"
    else:
        title = "Traits Assigned"


    embed = discord.Embed(
        title=title
    )
    embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)
    if len(assigned) > 0:
        assigned = ", ".join(list(map(lambda trait: f"`{trait}`", assigned)))
        embed.add_field(name="Assigned", value=assigned)

    if len(unassigned) > 0:
        unassigned = ", ".join(list(map(lambda trait: f"`{trait}`", unassigned)))
        embed.add_field(name="Not yet assigned", value=unassigned)
        embed.set_footer(text="Check your DMs to finish assigning the traits.")

    await ctx.reply(embed=embed)
