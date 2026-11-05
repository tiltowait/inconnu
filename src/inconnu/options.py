"""options.py - Various options for command parameters."""

from collections.abc import Awaitable, Callable
from typing import Any

import discord
from discord.commands import Option, OptionChoice

import services
from models import ImpairmentCategory, VChar
from utils.permissions import is_storyteller

type Autocomplete = Callable[[discord.AutocompleteContext], Awaitable[list[OptionChoice]]]
type Decorator = Callable[[Callable[..., Any]], Callable[..., Any]]


def ratings(low: int, high: int) -> list[OptionChoice]:
    """Creates a list of OptionChoices within the given range, inclusive."""
    return [OptionChoice(str(n), n) for n in range(low, high + 1)]


def character(description="The character to use", required=False) -> Option:
    """Return an Option that generates a list of player characters."""
    return Option(str, description, autocomplete=_character_autocomplete(), required=required)


def char_option(
    description="The character to use", required=False, param="character", *, allow_lookups=False
) -> Decorator:
    """A command decorator letting users choose a character. With allow_lookups,
    anyone may choose another player's characters (Haven's allow_lookups)."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func.__annotations__[param] = Option(
            str,
            description,
            name=param,
            autocomplete=_character_autocomplete(allow_lookups),
            required=required,
        )
        return func

    return decorator


def impairment_option(param="impairment_category") -> Decorator:
    """A command decorator letting users override a roll's Impairment category."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func.__annotations__[param] = Option(
            str,
            "Change the roll's Impairment category, or ignore Impairment",
            name=param,
            choices=[OptionChoice(choice.label, choice.value) for choice in ImpairmentCategory],
            required=False,
            default=None,
        )
        return func

    return decorator


def dice_option(param="dice") -> Decorator:
    """A command decorator letting users hide a roll's dice."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func.__annotations__[param] = Option(
            str,
            "Show or hide the dice from others",
            name=param,
            choices=[OptionChoice("Show", "show"), OptionChoice("Hide", "hide")],
            required=False,
            default="show",
        )
        return func

    return decorator


def player_option(
    param="player", description="The character's owner (Storyteller only)", required=False
) -> Decorator:
    """A command decorator letting users choose a user."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func.__annotations__[param] = Option(
            discord.Member,
            description,
            name=param,
            required=required,
        )
        return func

    return decorator


player = Option(discord.Member, "The character's owner (Storyteller only)", required=False)


# Helper functions


def _character_autocomplete(allow_lookups=False) -> Autocomplete:
    """An autocomplete listing the user's characters, or another player's if
    the user may look them up."""

    async def autocomplete(ctx: discord.AutocompleteContext) -> list[OptionChoice]:
        """Wrap _available_characters with the lookup permission."""
        return await _available_characters(ctx, allow_lookups)

    return autocomplete


async def _available_characters(
    ctx: discord.AutocompleteContext, allow_lookups: bool
) -> list[OptionChoice]:
    """Generate a list of the user's available characters."""
    if (guild := ctx.interaction.guild) is None or (user := ctx.interaction.user) is None:
        return []

    # Check if they're looking up a player and have lookup permissions
    spcs = []

    if (owner := (ctx.options.get("player") or ctx.options.get("current_owner"))) is not None:
        # Autocomplete gets the raw payload value, a string snowflake
        owner = int(owner)
        if owner != user.id and not (allow_lookups or await is_storyteller(user)):
            return [OptionChoice("Only Storytellers can look up other players", "")]
    else:
        owner = user.id

        if await is_storyteller(user):
            # Add SPCs
            spcs = await services.char_mgr.fetchall(guild.id, VChar.SPC_OWNER)
            spcs = [(spc.name, spc.id_str) for spc in spcs]

    chars = await services.char_mgr.fetchall(guild.id, owner)
    chars = [(char.name, char.id_str) for char in chars]
    chars.extend(spcs)

    name_search = ctx.value.casefold()

    found_chars = [
        OptionChoice(name, ident)
        for name, ident in chars
        if name.casefold().startswith(name_search or "")
    ]

    if len(found_chars) > 25:
        instructions = "Keep typing ..." if ctx.value else "Start typing a name."
        return [OptionChoice(f"Too many characters to display. {instructions}", "")]
    return found_chars
