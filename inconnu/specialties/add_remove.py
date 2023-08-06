"""Specialties addition and removal."""

import asyncio
from enum import Enum

import discord

import inconnu
from inconnu.models.vchar import VChar
from inconnu.specialties.tokenize import SYNTAX, tokenize
from inconnu.utils.haven import haven
from logger import Logger

__HELP_URL = "https://docs.inconnu.app/guides/quickstart/specialties"


class Action(Enum):
    """An enum representing the action state."""

    ADD = 0
    REMOVE = 1


class Category(str, Enum):
    """An enum representing a trait category."""

    SPECIALTY = "Specialty"
    POWER = "Power"

    @property
    def plural(self) -> str:
        """The category's plural form."""
        if self == Category.SPECIALTY:
            return "Specialties"
        return "Powers"


@haven(__HELP_URL)
async def add(ctx: discord.ApplicationContext, character, syntax: str, category: Category):
    """Add specialties to one or more of the character's traits."""
    await _add_or_remove(ctx, character, syntax, Action.ADD, category)


@haven(__HELP_URL)
async def remove(ctx: discord.ApplicationContext, character, syntax: str, category: Category):
    """Remove specialties from one or more of the character's traits."""
    await _add_or_remove(ctx, character, syntax, Action.REMOVE, category)


async def _add_or_remove(
    ctx: discord.ApplicationContext,
    character,
    syntax: str,
    action: Action,
    category: Category,
):
    """Perform the actual work of adding or removing a spec."""
    if action == Action.ADD:
        action = add_specialties
        title = category.plural + " added"
    else:
        action = remove_specialties
        title = category.plural + " removed"

    try:
        additions = action(character, syntax, category)
        embed = _make_embed(ctx, character, additions, title)
        view = inconnu.views.TraitsView(character, ctx.user)

        tasks = [ctx.respond(embed=embed, view=view, ephemeral=True), character.commit()]

        # Because the delta might be zero, only send an update report if
        # changes were actually made
        for _, delta in additions:
            if delta:
                cat = category.plural.lower()
                msg = f"__{ctx.user.mention} updated {character.name}'s {cat}__\n"
                msg += embed.description
                tasks.append(
                    inconnu.common.report_update(
                        ctx=ctx,
                        character=character,
                        title=title,
                        message=msg,
                        color=0xFF9400,
                    )
                )
                Logger.debug("SPECIALTIES: Delta found")
                break

        await asyncio.gather(*tasks)

    except SyntaxError as err:
        await inconnu.utils.error(
            ctx,
            err,
            ("Proper syntax", SYNTAX),
            ("Given", "```" + syntax + "```"),
            ("Reminder", "Don't leave a trailing `,`!"),
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
    embed.set_footer(text="See all specialties, powers, traits, and Disciplines with /traits list.")

    return embed


def add_specialties(character: VChar, syntax: str, category: Category) -> list:
    """Add specialties to the character."""
    return _mod_specialties(character, syntax, True, category)


def remove_specialties(character: VChar, syntax: str, _=None) -> list:
    """Remove specialties from a character."""
    return _mod_specialties(character, syntax, False, None)


def _mod_specialties(character: VChar, syntax: str, adding: bool, category: Category):
    """Do the actual work of adding or removing specialties."""
    tokens = tokenize(syntax)
    validate_tokens(character, tokens)

    if category == Category.SPECIALTY:
        add_method = VChar.add_specialties
    else:
        add_method = VChar.add_powers

    # We have the traits; add the specialties
    traits = []
    for trait, specs in tokens:
        if adding:
            new_trait, delta = add_method(character, trait, specs)
        else:
            new_trait, delta = character.remove_specialties(trait, specs)
        traits.append((new_trait, delta))

    return traits


def validate_tokens(character: VChar, tokens: list[tuple[str, list[str]]]):
    """Raise an exception if the character is missing one of the traits."""
    missing = []
    errs = []
    for trait, subtraits in tokens:
        if not character.has_trait(trait):
            missing.append(trait)
        if not errs:
            for subtrait in map(str.lower, subtraits):
                if subtrait == trait.lower():
                    errs.append("A subtrait can't have the same name as the parent trait.")

    if missing:
        if len(missing) == 1:
            # We want the part of the error with the character name to come first
            errs.insert(0, f"**{character.name}** has no trait named `{missing[0]}`.")
        else:
            missing = ", ".join(map(lambda t: f"`{t}`", missing))
            errs.insert(0, f"**{character.name}** doesn't have the following traits: {missing}.")

    if errs:
        raise inconnu.errors.TraitError("\n\n".join(errs))
