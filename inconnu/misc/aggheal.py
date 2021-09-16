"""misc/aggheal.py - Heal aggravated damage."""

import random
from types import SimpleNamespace

import discord

from .. import common
from ..character.display import trackmoji
from ..constants import DAMAGE
from ..vchar import errors, VChar

__HELP_URL = "https://www.inconnu-bot.com/#/"


async def aggheal(ctx, character: str):
    """Heal a point of aggravated damage."""
    try:
        tip = "`/aggheal` `character:CHARACTER`"
        character = await fetch_character(ctx, character, tip, __HELP_URL)

        if character.health.count(DAMAGE.aggravated) == 0:
            await ctx.respond(f"{character.name} has no aggravated damage to heal!", hidden=True)
            return

        outcome = __heal(character)
        await __display_outcome(ctx, character, outcome)

    except FetchError:
        pass


def __heal(character: VChar):
    """
    Heal agg damage.
    Does not check if the character has agg damage!
    """
    hunger_gain = 0
    for _ in range(3):
        if random.randint(1, 10) < 6:
            hunger_gain += 1

    frenzy = False
    if character.hunger + hunger_gain > 5:
        hunger_gain = 5 - character.hunger
        frenzy = True


    # Update the character
    character.hunger += hunger_gain
    character.health = DAMAGE.none + character.health[:-1]

    return SimpleNamespace(gain=hunger_gain, frenzy=frenzy)


async def __display_outcome(ctx, character, outcome):
    """Display the outcome of the healing."""
    gain = "Max Hunger" if character.hunger == 5 else f"Gain {outcome.gain} Hunger"
    embed = discord.Embed(
        title=f"Damage healed | {gain}",
    )
    embed.set_author(name=character.name, icon_url=ctx.author.avatar_url)

    embed.add_field(name="Health", value=trackmoji.emojify_track(character.health), inline=False)
    embed.add_field(name="Hunger", value=trackmoji.emojify_hunger(character.hunger), inline=False)

    if outcome.frenzy:
        embed.set_footer(text="ROLL FOR HUNGER FRENZY!")

    await ctx.respond(embed=embed)



class FetchError(Exception):
    """An error for when we are unable to fetch a character."""


async def fetch_character(ctx, character, tip, help_url, userid=None):
    """
    Attempt to fetch a character, presenting a selection dialogue if necessary.
    Args:
        ctx: The Discord context for displaying messages and retrieving guild info
        character (str): The name of the character to fetch. Optional.
        tip (str): The proper syntax for the command
        help_url (str): The URL of the button to display on any error messages
        userid (int): The ID of the user who owns the character, if different from the ctx author
    """
    try:
        userid = userid or ctx.author.id
        return VChar.fetch(ctx.guild.id, userid, character)

    except errors.UnspecifiedCharacterError as err:
        character = await common.select_character(ctx, err, help_url, ("Proper syntax", tip))

        if character is None:
            raise FetchError("No character was selected.") from err

        return character

    except errors.CharacterError as err:
        await common.present_error(ctx, err, help_url=help_url)
        raise FetchError(str(err)) from err
