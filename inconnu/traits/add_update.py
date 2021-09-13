"""traits/add.py - Add traits to a character."""

from types import SimpleNamespace

import discord

from .parser import parse_traits
from .traitwizard import TraitWizard
from .. import common
from ..vchar import errors, VChar

async def parse(ctx, allow_overwrite: bool, traits: str, character=None):
    """Add traits to a character."""
    try:
        character = VChar.strict_find(ctx.guild.id, ctx.author.id, character)
        traits = parse_traits(*traits.split())
        outcome = __handle_traits(character, traits, allow_overwrite)

        await __display_results(ctx, outcome, character.name)

        if len(outcome.unassigned) > 0:
            wizard = TraitWizard(ctx, character, outcome.unassigned)
            await wizard.begin()

    except (ValueError, SyntaxError) as err:
        await common.display_error(ctx, character.name, err)
    except errors.CharacterError as err:
        await common.display_error(ctx, ctx.author.display_name, err)
    except discord.errors.Forbidden:
        await ctx.respond(
            "**Whoops!** I can't DM your trait wizard. Please enable DMs and try again.",
            hidden=True
        )
        del wizard


def __handle_traits(character: VChar, traits: dict, overwriting: bool):
    """
    Add the rated traits to the character directly. Create a wizard for the rest.
    Args:
        character (VChar): The character's database ID
        traits (dict): The {str: Optional[int]} dict of traits
        overwriting (bool): Whether we allow overwrites
    All traits and ratings are assumed to be valid at this time.
    """
    partition = character.owned_traits(**traits)
    assigned = []
    unassigned = []

    if overwriting:
        error_traits = list(partition.unowned.keys())
        for trait, rating in partition.owned.items():
            if rating is None:
                unassigned.append(trait)
            else:
                character.update_trait(trait, rating)
                assigned.append(trait)

    else:
        error_traits = list(partition.owned.keys())
        for trait, rating in partition.unowned.items():
            if rating is None:
                unassigned.append(trait)
            else:
                character.add_trait(trait, rating)
                assigned.append(trait)

    return SimpleNamespace(
        assigned=assigned,
        unassigned=unassigned,
        errors=error_traits,
        editing=overwriting
    )


async def __display_results(ctx, outcome, char_name: str):
    """Display the results of the operation in a nice embed."""
    title = None
    if len(outcome.assigned) == 0 and len(outcome.unassigned) == 0 and len(outcome.errors) > 0:
        title = "Unable to Modify Traits"
    elif len(outcome.unassigned) > 0:
        title = "Entering Incognito Mode"
    else:
        title = "Traits Assigned"


    embed = discord.Embed(
        title=title
    )
    embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)
    if len(outcome.assigned) > 0:
        assigned = ", ".join(list(map(lambda trait: f"`{trait}`", outcome.assigned)))
        embed.add_field(name="Assigned", value=assigned)

    if len(outcome.unassigned) > 0:
        unassigned = ", ".join(list(map(lambda trait: f"`{trait}`", outcome.unassigned)))
        embed.add_field(name="Not yet assigned", value=unassigned)
        embed.set_footer(text="Check your DMs to finish assigning the traits.")

    if len(outcome.errors) > 0:
        errs = ", ".join(list(map(lambda trait: f"`{trait}`", outcome.errors)))
        if outcome.editing:
            field_name = "Error! You don't have these traits"
        else:
            field_name = "Error! You already have these traits"
        embed.add_field(name=field_name, value=errs, inline=False)

    await ctx.respond(embed=embed, hidden=True)
