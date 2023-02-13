"""Specialties addition and removal."""

from enum import Enum

import discord

import inconnu
from inconnu.models.vchar import VChar
from inconnu.specialties.tokenize import SYNTAX, tokenize
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app"


class Action(Enum):
    """An enum representing the action state."""

    ADD = 0
    REMOVE = 1


@haven(__HELP_URL)
async def add(ctx: discord.ApplicationContext, character, syntax: str):
    """Add specialties to one or more of the character's traits."""
    await _add_or_remove(ctx, character, syntax, Action.ADD)


@haven(__HELP_URL)
async def remove(ctx: discord.ApplicationContext, character, syntax: str):
    """Remove specialties from one or more of the character's traits."""
    await _add_or_remove(ctx, character, syntax, Action.REMOVE)


async def _add_or_remove(
    ctx: discord.ApplicationContext,
    character,
    syntax: str,
    action: Action,
):
    """Perform the actual work of adding or removing a spec."""
    if action == Action.ADD:
        action = add_specialties
        title = "Specialties added"
    else:
        action = remove_specialties
        title = "Specialties removed"

    try:
        additions = action(character, syntax)
        embed = _make_embed(ctx, character, additions, title)
        view = inconnu.views.TraitsView(character, ctx.user)

        await ctx.respond(embed=embed, view=view, ephemeral=True)
        await character.commit()

    except SyntaxError as err:
        await inconnu.utils.error(
            ctx,
            err,
            ("Proper syntax", SYNTAX),
            title="Invalid syntax",
        )
    except inconnu.errors.TraitError as err:
        await inconnu.utils.error(ctx, err)


def _make_embed(
    ctx: discord.ApplicationContext,
    character: VChar,
    additions: list,
    title: str,
):
    """Create the embed."""
    entries = []
    for trait, delta in additions:
        delta_str = inconnu.utils.format_join(delta, ", ", "`", "*No change*")

        entry = f"**{trait.name}:** {delta_str}"
        if len(delta) != len(trait.specialties):
            specs_str = inconnu.utils.format_join(trait.specialties, ", ", "*", "*None*")
            entry += f"\n***All:*** {specs_str}\n"
            entry = "\n" + entry
        entries.append(entry)

    content = "\n".join(entries).strip()
    embed = inconnu.utils.VCharEmbed(ctx, character, title=title, description=content)
    embed.set_footer(text="See all specialties, traits, and Disciplines with /traits list.")

    return embed


def add_specialties(character: VChar, syntax: str) -> list:
    """Add specialties to the character."""
    return _mod_specialties(character, syntax, True)


def remove_specialties(character: VChar, syntax: str) -> list:
    """Remove specialties from a character."""
    return _mod_specialties(character, syntax, False)


def _mod_specialties(character: VChar, syntax: str, adding: bool):
    """Do the actual work of adding or removing specialties."""
    tokens = tokenize(syntax)
    validate_tokens(character, tokens)

    # We have the traits; add the specialties
    traits = []
    for trait, specs in tokens:
        if adding:
            new_trait, delta = character.add_specialties(trait, specs)
        else:
            new_trait, delta = character.remove_specialties(trait, specs)
        traits.append((new_trait, delta))

    return traits


def validate_tokens(character: VChar, tokens: list[tuple[str, list[str]]]):
    """Raise an exception if the character is missing one of the traits."""
    missing = []
    for trait, _ in tokens:
        if not character.has_trait(trait):
            missing.append(trait)

    if missing:
        if len(missing) == 1:
            err_msg = f"**{character.name}** has no trait named `{missing[0]}`."
        else:
            missing = ", ".join(map(lambda t: f"`{t}`", missing))
            err_msg = f"**{character.name}** doesn't have the following traits: {missing}."
        raise inconnu.errors.TraitError(err_msg)
