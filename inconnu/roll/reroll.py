"""reroll.py - Facilities for implementing Willpower re-roll strategies."""

import random

import discord

from .dicethrow import DiceThrow
from .rollresult import RollResult

__MAX_REROLL = 3

async def wait_for_reroll(ctx, message, old_roll):
    """
    Wait for the user to click a re-roll button.
    Args:
        ctx: The Discord context, which includes the accepted user
        message: The Discord message to watch
        old_roll (RollResult): The original dice roll
    """
    waiting = True

    while waiting:
        btn = await message.wait_for("button", ctx.bot, timeout=60)
        await btn.respond()

        if ctx.author.id != btn.author.id:
            # We only want the original roller to be able to press these buttons
            return

        new_dice = None
        descriptor = None

        if btn.custom_id == "reroll_failures":
            new_dice = __reroll_failures(old_roll.normal.dice)
            descriptor = "Rerolling Failures"

        elif btn.custom_id == "maximize_criticals":
            new_dice = __maximize_criticals(old_roll.normal.dice)
            descriptor = "Maximizing Criticals"

        elif btn.custom_id == "avoid_messy":
            new_dice = __avoid_messy(old_roll.normal.dice)
            descriptor = "Avoiding Messy Critical"

        new_throw = DiceThrow(new_dice)
        new_results = RollResult(new_throw, old_roll.hunger, old_roll.difficulty)
        new_results.descriptor = descriptor

        return new_results


def __reroll_failures(dice: list) -> list:
    """Re-roll up to three failing dice."""
    new_dice = []
    rerolled = 0

    for die in dice:
        if die >= 6 or rerolled == __MAX_REROLL:
            new_dice.append(die)
        else:
            new_dice.append(__d10())
            rerolled += 1

    return new_dice


def __maximize_criticals(dice: list) -> list:
    """Re-roll up to three non-critical dice."""
    new_dice = []
    rerolled = 0

    for die in dice:
        if die == 10 or rerolled == __MAX_REROLL:
            new_dice.append(die)
        else:
            new_dice.append(__d10())
            rerolled += 1

    return new_dice


def __avoid_messy(dice: list) -> list:
    """Re-roll up to three critical dice."""
    new_dice = []
    rerolled = 0

    for die in dice:
        if die != 10 or rerolled == __MAX_REROLL:
            new_dice.append(die)
        else:
            new_dice.append(__d10())
            rerolled += 1

    return new_dice


def __d10() -> int:
    """Roll a d10."""
    return random.randint(1, 10)
