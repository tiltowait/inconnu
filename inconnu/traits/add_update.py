"""traits/add.py - Add traits to a character."""

from types import SimpleNamespace

import discord
from discord_ui.components import LinkButton

from .parser import parse_traits
from .traitwizard import TraitWizard
from .. import common
from ..constants import SUPPORT_URL
from ..settings import Settings
from ..vchar import VChar

__HELP_URL = {
    False: "https://www.inconnu-bot.com/#/trait-management?id=adding-traits",
    True: "https://www.inconnu-bot.com/#/trait-management?id=updating-traits"
}


async def add(ctx, traits: str, character: str):
    """Add traits to a character. Wrapper for add_update."""
    await __parse(ctx, False, traits, character)


async def update(ctx, traits: str, character: str):
    """Update a character's traits. Wrapper for add_update."""
    await __parse(ctx, True, traits, character)


async def __parse(ctx, allow_overwrite: bool, traits: str, character: str):
    """Add traits to a character."""
    try:
        key = "update" if allow_overwrite else "add"
        tip = f"`/traits {key}` `traits:{traits}` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL[allow_overwrite])

        traits = parse_traits(*traits.split())
        outcome = __handle_traits(character, traits, allow_overwrite)

        await __display_results(ctx, outcome, character.name)

        if len(outcome.unassigned) > 0:
            wizard = TraitWizard(ctx, character, outcome.unassigned, allow_overwrite)
            await wizard.begin()

    except (ValueError, SyntaxError) as err:
        await common.present_error(
            ctx,
            err,
            character=character,
            help_url=__HELP_URL[allow_overwrite]
        )
    except discord.errors.Forbidden:
        await ctx.respond(
            "**Whoops!** Your DMs are closed. Please open them so I can send your trait wizard.",
            hidden=True
        )
        del wizard
    except common.FetchError:
        pass


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
    """Display the results of the operation."""
    if Settings.accessible(ctx.author):
        await __results_text(ctx, outcome, char_name)
    else:
        await __results_embed(ctx, outcome, char_name)


async def __results_embed(ctx, outcome, char_name: str):
    """Display the results of the operation in a nice embed."""
    if len(outcome.assigned) == 0 and len(outcome.unassigned) == 0 and len(outcome.errors) > 0:
        title = "Unable to Modify Traits"
    elif len(outcome.unassigned) > 0:
        title = "Entering Incognito Mode"
    else:
        title = "Traits Assigned"

    embed = discord.Embed(
        title=title
    )
    embed.set_author(name=char_name, icon_url=ctx.author.display_avatar)
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


async def __results_text(ctx, outcome, char_name: str):
    """Display the results in plain text."""
    contents = [f"{char_name}: Trait Assignment\n"]

    if len(outcome.assigned) > 0:
        assigned = ", ".join(list(map(lambda trait: f"`{trait}`", outcome.assigned)))
        contents.append(f"Assigned: {assigned}")

    footer = None
    if len(outcome.unassigned) > 0:
        unassigned = ", ".join(list(map(lambda trait: f"`{trait}`", outcome.unassigned)))
        contents.append(f"Not yet assigned: {unassigned}")
        footer = "Check your DMs to finish assigning the traits."

    if len(outcome.errors) > 0:
        errs = ", ".join(list(map(lambda trait: f"`{trait}`", outcome.errors)))
        if outcome.editing:
            err_field = "Error! You don't have " + errs
        else:
            err_field = "Error! You already have " + errs
        contents.append(err_field)

    if footer is not None:
        contents.append(f"```{footer}```")

    await ctx.respond("\n".join(contents), hidden=True)


async def traits_help(ctx):
    """Display a help message for managing traits."""
    embed = discord.Embed(
        title="Traits Management",
        description="This command group allows you to add, remove, or update character traits."
    )
    embed.set_author(name=ctx.bot.user.display_name, icon_url=ctx.bot.user.avatar)
    embed.set_footer(text="Traits may be used in rolls. See /help for more info.")

    embed.add_field(
        name="Add Traits",
        value="`/traits add`\n**Example:** `/traits add traits:Oblivion=3 Auspex=2`",
        inline=False
    )

    embed.add_field(
        name="Delete Traits",
        value="`/traits delete`\n**Example:** `/traits delete traits:Oblivion`",
        inline=False
    )

    embed.add_field(
        name="Modify Traits",
        value="`/traits update`\n**Example:** `/traits update traits:Oblivion=2`",
        inline=False
    )

    buttons = [
        LinkButton("https://www.inconnu-bot.com/#/trait-management", "Documentation"),
        LinkButton(SUPPORT_URL, "Support")
    ]

    await ctx.respond(embed=embed, components=buttons)
