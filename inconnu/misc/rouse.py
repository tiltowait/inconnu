"""misc/rouse.py - Perform rouse checks."""
# pylint: disable=too-many-arguments

import asyncio
from types import SimpleNamespace

import discord

import inconnu
from inconnu.vchar import VChar

__HELP_URL = "https://www.inconnu.app/#/additional-commands?id=rouse-checks"


async def rouse(
    ctx, count: int, character: str, purpose: str, reroll: bool, oblivion="show", message=None
):
    """
    Perform a remorse check on a given character and display the results.
    Args:
        count (int): The number of rouse checks to make
        character (str): (Optional): The name of a character
        purpose (str): The reason for the rouse
        reroll (bool): Whether failures should be re-rolled
        oblivion (bool, default False): Whether to show the Oblivion message.
    """
    if not isinstance(character, VChar):
        haven = inconnu.utils.Haven(
            ctx,
            character=character,
            tip="`/rouse` `character:CHARACTER`",
            char_filter=_can_rouse,
            help=__HELP_URL,
        )
        character = await haven.fetch()

    if character.splat == "mortal":
        await ctx.respond("Mortals can't make Rouse checks.", ephemeral=True)
    elif character.splat == "ghoul":
        await __damage_ghoul(ctx, character)
    else:
        # Vampire
        outcome = await __rouse_roll(ctx.guild, character, count, reroll)
        update_msg = f"**{character.name}** "
        if outcome.gain:
            update_msg += f"__failed__ a Rouse check. Hunger is now `{character.hunger}`."
        else:
            update_msg += f"__passed__ a Rouse check. Hunger remains `{character.hunger}`."

        inter = await __display_outcome(ctx, character, outcome, purpose, oblivion, message)
        msg = await inconnu.get_message(inter)

        if character.hunger >= 4:
            color = inconnu.constants.ROUSE_FAIL_COLOR
        else:
            color = discord.Embed.Empty

        await inconnu.common.report_update(
            ctx=ctx,
            msg=msg,
            character=character,
            title="Rouse Check",
            message=update_msg,
            color=color,
        )


def _can_rouse(character):
    """Raises an error if the character is mortal."""
    if character.splat == "mortal":
        raise inconnu.vchar.errors.CharacterError(f"{character.name} is a mortal.")


def __make_title(outcome):
    """Create the title for the output message."""
    if outcome.total == 1:
        title = "Rouse Success" if outcome.successes == 1 else "Rouse Failure"
    else:
        successes = inconnu.common.pluralize(outcome.successes, "success")
        failures = inconnu.common.pluralize(outcome.failures, "failure")
        title = f"Rouse: {successes}, {failures}"

    return title


async def __display_outcome(ctx, character: VChar, outcome, purpose, oblivion, message):
    """Process the rouse result and display to the user."""
    title = __make_title(outcome)

    if "ailure" in title and "0 fail" not in title:
        color = inconnu.constants.ROUSE_FAIL_COLOR
        thumbnail = "https://www.inconnu.app/images/assets/hunger-filled.webp"
    else:
        color = None
        thumbnail = "https://www.inconnu.app/images/assets/hunger-unfilled.webp"

    if outcome.frenzy:
        custom = [("Hunger 5 Rouse Failure", "If awakening: Torpor. Otherwise: Roll for frenzy!")]
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
        stains_txt = inconnu.common.pluralize(outcome.stains, "stain")

        if oblivion == "show":
            footer.append(f"If this was an Oblivion roll, gain {stains_txt}!")
        elif oblivion == "apply":
            await asyncio.gather(
                character.set_stains(character.stains + outcome.stains),
                character.log("stains", outcome.stains),
            )
            fields.append((f"Gain {stains_txt}", inconnu.character.DisplayField.HUMANITY))

    footer = "\n".join(footer)

    view = inconnu.views.FrenzyView(character, 4) if outcome.frenzy else None

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
    )


async def __damage_ghoul(ctx, ghoul):
    """Apply Aggravated damage to a ghoul and display."""
    await ghoul.set_aggravated_hp(ghoul.aggravated_hp + 1)
    await inconnu.character.display(
        ctx,
        ghoul,
        title="Ghoul Rouse Damage",
        message="Ghouls take Aggravated damage instead of making a Rouse check.",
        fields=[("Health", inconnu.character.DisplayField.HEALTH)],
        footer="V5 Core, p.234",
    )


async def __rouse_roll(guild, character: VChar, rolls: int, reroll: bool):
    """Perform a Rouse roll."""
    successes = 0
    failures = 0
    stains = 0

    oblivion = await inconnu.settings.oblivion_stains(guild)

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
    await character.set_hunger(starting_hunger + failures)
    gain = starting_hunger - character.hunger

    await character.log("rouse", rolls)

    return SimpleNamespace(
        total=rolls,
        successes=successes,
        failures=failures,
        stains=stains,
        frenzy=frenzy,
        gain=gain,
        reroll=reroll,
    )
