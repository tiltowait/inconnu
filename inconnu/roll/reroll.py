"""reroll.py - Facilities for implementing Willpower re-roll strategies."""

import random

from .dicethrow import DiceThrow

__MAX_REROLL = 3

async def wait_for_reroll(ctx, message, old_roll):
    """
    Wait for the user to click a re-roll button.
    Args:
        ctx: The Discord context, which includes the accepted user
        message: The Discord message to watch
        old_roll (RollResult): The original dice roll

    Raises asyncio.exceptions.TimeoutError if the interaction times out.
    """
    btn = await message.wait_for("button", ctx.bot)

    while ctx.author.id != btn.author.id:
        # We only want the original roller to be able to press these buttons
        await btn.respond("Sorry, you can't reroll for another player.", hidden=True)
        btn = await message.wait_for("button", ctx.bot)

    await btn.respond()

    return reroll(btn.custom_id, old_roll)


def reroll(strategy, original):
    """Perform a reroll based on a given strategy."""
    new_dice = None
    descriptor = None

    rerolled = original

    if strategy == "reroll_failures":
        new_dice = __reroll_failures(original.normal.dice)
        rerolled.strategy = "failures"
        descriptor = "Rerolling Failures"

    elif strategy == "maximize_criticals":
        new_dice = __maximize_criticals(original.normal.dice)
        rerolled.strategy = "criticals"
        descriptor = "Maximizing Criticals"

    elif strategy == "avoid_messy":
        new_dice = __avoid_messy(original.normal.dice)
        rerolled.strategy = "messy"
        descriptor = "Avoiding Messy Critical"

    elif strategy == "risky":
        new_dice = __risky_avoid_messy(original.normal.dice)
        rerolled.strategy = "risky"
        descriptor = "Avoid Messy (Risky)"

    new_throw = DiceThrow(new_dice)
    rerolled.normal = new_throw
    rerolled.descriptor = descriptor

    return rerolled


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

    # If there are 3 or more failure dice, we don't need to re-roll any successes.
    # To avoid accidentally skipping a die that needs to be re-rolled, we will
    # convert successful dice until our total failures equals 3

    # Technically, we could do this in two passes: re-roll failures, then re-
    # roll non-criticals until we hit 3 re-rolls. It would certainly be the more
    # elegant solution. However, that method would frequently result in the same
    # die being re-rolled twice. This isn't technically against RAW, but it's
    # against the spirit and furthermore increases the likelihood of bug reports
    # due to people seeing dice frequently not being re-rolled when they expect
    # them to be.

    # Thus, we use this ugly method.
    total_failures = len(list(filter(lambda die: die < 6, dice)))
    if total_failures < __MAX_REROLL:
        for index, die in enumerate(dice):
            if 6 <= die < 10: # Non-critical success
                dice[index] = 1
                total_failures += 1

                if total_failures == __MAX_REROLL:
                    break

    # We have as many re-rollable dice as we can
    new_dice = []
    rerolled = 0

    for die in dice:
        if die >= 6 or rerolled == __MAX_REROLL:
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


def __risky_avoid_messy(dice: list) -> list:
    """Re-roll up to three critical dice plus one or two failing dice."""
    new_dice = []
    tens_remaining = dice.count(10)
    fails_remaining = 3 - tens_remaining

    for die in dice:
        if tens_remaining > 0 and die == 10:
            new_dice.append(__d10())
            tens_remaining -= 1
        elif die < 6 and fails_remaining > 0:
            new_dice.append(__d10())
            fails_remaining -= 1
        else:
            new_dice.append(die)

    return new_dice


def __d10() -> int:
    """Roll a d10."""
    return random.randint(1, 10)
