"""misc/rouse.py - Perform rouse checks."""

from typing import NamedTuple, cast

import discord

import constants
import errors
import inconnu
import services
import ui
from ctx import AppCtx, AppInvocation
from models import VChar
from services.haven import haven
from utils import get_message
from utils.text import pluralize
from utils.urls import docs_url, web_asset

__HELP_URL = docs_url("guides/gameplay-shortcuts#rouse-checks")


class _RouseOutcome(NamedTuple):
    """The results of a set of Rouse checks."""

    total: int
    successes: int
    failures: int
    stains: int
    frenzy: bool
    gain: int
    reroll: bool


def _can_rouse(character: VChar):
    """Raises an error if the character is mortal."""
    if character.splat == "mortal":
        raise errors.CharacterError(f"{character.name} is a mortal.")


@haven(__HELP_URL, _can_rouse)
async def rouse(
    ctx: AppCtx,
    character: VChar,
    count: int,
    purpose: str | None,
    reroll: bool,
    oblivion: str | bool = "show",
    message: str | None = None,
    ephemeral=False,
):
    """Perform Rouse checks for the selected character and display the results.
    See perform_rouse() for the arguments."""
    await perform_rouse(ctx, character, count, purpose, reroll, oblivion, message, ephemeral)


async def perform_rouse(
    ctx: AppInvocation,
    character: VChar,
    count: int,
    purpose: str | None,
    reroll: bool,
    oblivion: str | bool = "show",
    message: str | None = None,
    ephemeral=False,
):
    """
    Perform Rouse checks for a character who's already been chosen, and display
    the results. Ghouls take Aggravated damage instead.
    Args:
        character (VChar): The vampire or ghoul making the checks
        count (int): The number of Rouse checks to make
        purpose (str | None): The reason for the Rouse
        reroll (bool): Whether failures should be re-rolled
        oblivion (str | bool, default "show"): Whether to "show" the Oblivion
            stains message, "apply" the stains, or neither (False)
        message (str | None): A message to display with the outcome
        ephemeral (bool, default False): Whether only the user sees the outcome
    """
    if character.splat == "ghoul":
        await __damage_ghoul(ctx, character, ephemeral)
    else:
        # Vampire. Characters only exist in guilds.
        guild = cast(discord.Guild, ctx.guild)
        outcome = await __rouse_roll(guild, character, count, reroll)
        update_msg = f"**{character.name}** "
        if outcome.gain:
            update_msg += f"__failed__ a Rouse check. Hunger is now `{character.hunger}`."
        else:
            update_msg += f"__passed__ a Rouse check. Hunger remains `{character.hunger}`."

        await character.save()
        inter = await __display_outcome(
            ctx, character, outcome, purpose, oblivion, message, ephemeral
        )
        msg = await get_message(inter)

        if character.hunger >= 4:
            color = constants.ROUSE_FAIL_COLOR
        else:
            color = None

        await services.post_update(
            ctx=ctx,
            msg=msg,
            character=character,
            title="Rouse Check",
            message=update_msg,
            color=color,
        )

        # Yes, we already committed. This is because pre_update() clamps Hunger
        # within valid boundaries. Unfortunately, __display_outcome() runs
        # VChar.log(), which needs to be saved.
        # TODO: Move logging outside of __display_outcome()
        await character.save()


def __make_title(outcome: _RouseOutcome) -> str:
    """Create the title for the output message."""
    if outcome.total == 1:
        title = "Rouse Success" if outcome.successes == 1 else "Rouse Failure"
    else:
        successes = pluralize(outcome.successes, "success")
        failures = pluralize(outcome.failures, "failure")
        title = f"Rouse: {successes}, {failures}"

    return title


async def __display_outcome(
    ctx: AppInvocation,
    character: VChar,
    outcome: _RouseOutcome,
    purpose: str | None,
    oblivion: str | bool,
    message: str | None,
    ephemeral: bool,
) -> AppInvocation | discord.Interaction | discord.WebhookMessage:
    """Process the rouse result and display to the user."""
    title = __make_title(outcome)

    if "ailure" in title and "0 fail" not in title:
        color = constants.ROUSE_FAIL_COLOR
        thumbnail = web_asset("hunger-filled.webp")
    else:
        color = None
        thumbnail = web_asset("hunger-unfilled.webp")

    if outcome.frenzy:
        if outcome.failures > 0:
            custom = [
                ("Hunger 5 Rouse Failure", "If awakening: Torpor. Otherwise: Roll for frenzy!")
            ]
        else:
            custom = [("Hunger 5 Rouse Check", "Roll for frenzy!")]
    else:
        custom = None

    footer = []
    fields = [
        ("New Hunger" if "ailure" in title else "Hunger", inconnu.character.DisplayField.HUNGER)
    ]

    if purpose is not None:
        footer.append(purpose)
    if outcome.reroll:
        footer.append("Re-rolling failures")
    if outcome.stains > 0:
        stains_txt = pluralize(outcome.stains, "stain")

        if oblivion == "show":
            footer.append(f"If this was an Oblivion roll, gain {stains_txt}!")
        elif oblivion == "apply":
            character.stains += outcome.stains
            character.log("stains", outcome.stains)
            fields.append((f"Gain {stains_txt}", inconnu.character.DisplayField.HUMANITY))

    footer = "\n".join(footer)

    view = ui.views.FrenzyView(character, 4, ctx.user.id) if outcome.frenzy else None

    return await inconnu.character.display(
        ctx,
        character,
        title=title,
        footer=footer,
        message=message,
        fields=fields,
        custom=custom,
        color=color,
        thumbnail=thumbnail,
        view=view,
        ephemeral=ephemeral,
    )


async def __damage_ghoul(ctx: AppInvocation, ghoul: VChar, ephemeral: bool):
    """Apply Aggravated damage to a ghoul and display."""
    ghoul.set_aggravated_hp(ghoul.aggravated_hp + 1)
    await inconnu.character.display(
        ctx,
        ghoul,
        title="Ghoul Rouse Damage",
        message="Ghouls take Aggravated damage instead of making a Rouse check.",
        fields=[("Health", inconnu.character.DisplayField.HEALTH)],
        footer="V5 Core, p.234",
        ephemeral=ephemeral,
    )
    await ghoul.save()


async def __rouse_roll(
    guild: discord.Guild, character: VChar, rolls: int, reroll: bool
) -> _RouseOutcome:
    """Perform a Rouse roll."""
    successes = 0
    failures = 0
    stains = 0

    oblivion = await services.settings.oblivion_stains(guild)

    for _ in range(rolls):
        die = inconnu.d10()
        if reroll and die < 6:
            die = inconnu.d10()

        if die in oblivion:
            stains += 1

        if die >= 6:
            successes += 1
        else:
            failures += 1

    starting_hunger = character.hunger
    frenzy = starting_hunger == 5
    character.hunger += failures
    gain = starting_hunger - character.hunger

    character.log("rouse", rolls)

    return _RouseOutcome(
        total=rolls,
        successes=successes,
        failures=failures,
        stains=stains,
        frenzy=frenzy,
        gain=gain,
        reroll=reroll,
    )
