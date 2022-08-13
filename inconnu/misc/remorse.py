"""misc/remorse.py - Perform a remorse check."""

import asyncio
from types import SimpleNamespace as SN

import discord

import inconnu

from ..vchar import VChar

__HELP_URL = "https://www.inconnu.app/#/additional-commands?id=remorse-checks"


async def remorse(ctx, character=None, minimum=1):
    """Perform a remorse check on a given character."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        tip="`/remorse` `character:CHARACTER`",
        char_filter=_can_remorse,
        errmsg="None of your characters have any stains!",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    # Character obtained
    if character.stains == 0:
        await ctx.respond(f"{character.name} has no stains! No remorse necessary.", ephemeral=True)
        return

    outcome = await __remorse_roll(character, minimum)
    inter = await __display_outcome(ctx, character, outcome)
    await __report(ctx, inter, character, outcome.remorseful)


def _can_remorse(character):
    """Raise an exception if we have no stains."""
    if character.stains == 0:
        raise inconnu.errors.CharacterError(f"{character.name} has no stains.")


async def __display_outcome(ctx, character: VChar, outcome):
    """Process the remorse result and display to the user."""
    title = "Remorse Success" if outcome.remorseful else "Remorse Fail"
    if outcome.remorseful:
        footer = "You keep the Beast at bay. For now."
        color = 0x7777FF
    else:
        footer = "The downward spiral continues ..."
        color = 0x5C0700

    footer += "\nDice: " + ", ".join(map(str, outcome.dice))

    if outcome.overrode:
        dice = inconnu.common.pluralize(outcome.minimum, "die")
        footer += f"\nOverride: Rolled {dice} instead of {outcome.nominal}"

    return await inconnu.character.display(
        ctx,
        character,
        title=title,
        footer=footer,
        color=color,
        fields=[("Humanity", inconnu.character.DisplayField.HUMANITY)],
    )


async def __remorse_roll(character: VChar, minimum: int) -> SN:
    """Perform a remorse roll."""
    unfilled = 10 - character.humanity - character.stains
    rolls = max(unfilled, minimum)
    overrode = unfilled < minimum and minimum > 1
    nominal = unfilled if unfilled > 0 else 1
    successful = False

    dice = []
    for _ in range(rolls):
        throw = inconnu.d10()
        dice.append(throw)
        if throw >= 6:
            successful = True

    tasks = []
    if not successful:
        tasks.append(character.set_humanity(character.humanity - 1))
        tasks.append(character.log("degen"))
    else:
        tasks.append(character.set_stains(0))

    tasks.append(character.log("remorse"))
    await asyncio.gather(*tasks)

    return SN(remorseful=successful, minimum=minimum, dice=dice, overrode=overrode, nominal=nominal)


async def __report(ctx, inter, character, remorseful):
    """Generate the task to display the remorse outcome for the update channel."""
    if remorseful:
        verbed = "passed"
        humanity_str = f"Humanity remains at `{character.humanity}`."
    else:
        verbed = "failed"
        humanity_str = f"Humanity drops to `{character.humanity}`."

    msg = await inconnu.get_message(inter)

    await inconnu.common.report_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title="Remorse Success" if remorseful else "Remorse Failure",
        message=f"**{character.name}** {verbed} a Remorse test.\n{humanity_str}",
        color=0x5E005E if not remorseful else discord.Embed.Empty,
    )
