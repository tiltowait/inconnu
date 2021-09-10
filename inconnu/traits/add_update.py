"""traits/add.py - Add traits to a character."""

import discord

from .parser import parse_traits
from .traitwizard import TraitWizard
from .. import common
from ..vchar import errors, VChar

async def parse(ctx, allow_overwrite: bool, traits: str, character=None):
    """Add traits to a character."""
    character = None

    # Got the character
    try:
        character = VChar.strict_find(ctx.guild.id, ctx.author.id, character)
        traits = parse_traits(*traits.split())
        assigned_traits, wizard_traits = __handle_traits(character, traits, allow_overwrite)

        await __display_results(ctx, assigned_traits, wizard_traits, character.name)

        if len(wizard_traits) > 0:
            wizard = TraitWizard(ctx, character, wizard_traits)
            await wizard.begin()

    except (ValueError, SyntaxError, errors.CharacterError) as err:
        name = character.name if character is not None else ctx.author.display_name
        await common.display_error(ctx, name, err)


def __handle_traits(character: VChar, traits: dict, overwriting: bool):
    """
    Add the rated traits to the character directly. Create a wizard for the rest.
    Args:
        character (VChar): The character's database ID
        traits (dict): The {str: Optional[int]} dict of traits
        overwriting (bool): Whether we allow overwrites
    All traits and ratings are assumed to be valid at this time.
    """
    assigned_traits = []
    wizard_traits = []
    for trait, rating in traits.items():
        if rating is None:
            wizard_traits.append(trait)
            continue

        if overwriting:
            character.update_trait(trait, rating)
        else:
            character.add_trait(trait, rating)

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

    await ctx.respond(embed=embed, hidden=True)
