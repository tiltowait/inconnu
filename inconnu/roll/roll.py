"""rollresult.py - Class for calculating the results of a roll."""

import random

import bson

from .dicethrow import DiceThrow

__MAX_REROLL = 3


class Roll:
    """A container class that determines the result of a roll."""

    def __init__(self, pool, hunger, difficulty, pool_str=None, syntax=None):
        """
        Args:
            pool (int): The pool's total size, including hunger
            hunger (int): The rolled hunger dice
            difficulty (int): The target number of successes
            pool_str (Optional[int]): The pool's attribute + skill representation
        """
        self.id = bson.objectid.ObjectId() # pylint: disable=invalid-name

        if not 1 <= pool <= 100:
            raise ValueError(f"Pool must be between 1 and 100. (Got {pool}.)")

        normal_dice = max(0, pool - hunger)

        self.normal = DiceThrow(normal_dice)
        self.hunger = DiceThrow(hunger)
        self.difficulty = difficulty
        self.strategy = None
        self.descriptor = None

        if syntax is None:
            self.syntax = None
        elif isinstance(syntax, list):
            self.syntax = " ".join(map(str, syntax))
        else:
            self.syntax = syntax

        if pool_str is not None and not pool_str.isdigit():
            self.pool_str = pool_str
        else:
            self.pool_str = None


    # We could technically do this with stored properties, but the math is extremely
    # fast, so we will do it this way for legibility. This will also more easily let
    # us perform Willpower re-rolls.

    # Embed data

    @property
    def embed_color(self):
        """Determine the Discord embed color based on the result of the roll."""
        if self.is_critical:
            return 0x00FF00 # Green
        if self.is_messy:
            return 0xEA3323 # Red-orange
        if self.is_successful:
            return 0x7777FF # Blurple-ish
        if self.is_failure:
            return 0x808080 # Gray
        if self.is_total_failure:
            return 0x000000 # Black

        # Bestial failure
        return 0x5C0700 # Dark red


    @property
    def main_takeaway(self):
        """The roll's main takeaway--i.e. "SUCCESS", "FAILURE", etc."""
        if self.is_critical:
            return "**CRITICAL!**"
        if self.is_messy:
            return "**MESSY CRITICAL!**"
        if self.is_successful:
            return "**SUCCESS!**"
        if self.is_failure:
            return "**FAILURE!**"
        if self.is_total_failure:
            return "**TOTAL FAILURE!**"

        # Bestial failure
        return "**BESTIAL FAILURE!**"


    @property
    def outcome(self):
        """Simplified version of main_takeaway. Used in logs."""
        if self.is_critical:
            return "critical"
        if self.is_messy:
            return "messy"
        if self.is_successful:
            return "success"
        if self.is_failure:
            return "fail"
        if self.is_total_failure:
            return "total_fail"

        # Bestial failure
        return "bestial"


    # Roll Reflection

    @property
    def pool(self):
        """The total number of dice rolled."""
        return self.normal.count + self.hunger.count


    @property
    def total_successes(self):
        """The total number of successes."""
        total_tens = self.normal.tens + self.hunger.tens
        crits = total_tens - (total_tens % 2)

        return self.normal.successes + self.hunger.successes + crits


    @property
    def margin(self):
        """Return the roll's success margin."""
        return self.total_successes - self.difficulty


    @property
    def is_critical(self):
        """Return true if the roll is a critical, but not messy, success."""
        critical = self.normal.tens >= 2 and self.hunger.tens == 0
        return critical and self.is_successful


    @property
    def is_messy(self):
        """Return true if the roll is a messy critical."""
        messy = (self.normal.tens + self.hunger.tens) >= 2 and self.hunger.tens > 0
        return messy and self.is_successful


    @property
    def is_successful(self):
        """Return true if the roll meets or exceeds its target."""
        return self.total_successes >= self.difficulty and self.total_successes > 0


    @property
    def is_failure(self):
        """Return true if the target successes weren't achieved, but it isn't bestial."""
        return (self.hunger.ones == 0 and self.total_successes > 0) and not self.is_successful


    @property
    def is_total_failure(self):
        """Return true if no successes were rolled, and no ones on hunger dice."""
        return self.total_successes == 0 and self.hunger.ones == 0


    @property
    def is_bestial(self):
        """Return true if the roll is a bestial failure."""
        bestial = self.hunger.ones > 0
        return bestial and not self.is_successful


    # Re-roll strategies

    @property
    def can_reroll_failures(self):
        """Whether there are any non-Hunger failures to re-roll."""
        return self.normal.failures > 0


    @property
    def can_maximize_criticals(self):
        """Whether there are any non-critical non-Hunger failures to re-roll."""
        if self.normal.count + self.hunger.count < 2:
            return False
        if self.normal.count == 1:
            return self.normal.tens == 0 and self.hunger.tens > 0

        return self.normal.tens != self.normal.count


    @property
    def can_avoid_messy_critical(self):
        """Whether it's possible to avoid a messy critical, assuming we have one."""
        if not self.is_messy:
            return False

        return self.hunger.tens == 1


    @property
    def can_risky_messy_critical(self):
        """Whether a messy critical is possible *and* there are failures to re-roll."""
        return self.can_avoid_messy_critical and self.normal.failures > 0


    def reroll(self, strategy):
        """Perform a reroll based on a given strategy."""
        if strategy == "reroll_failures":
            new_dice = _reroll_failures(self.normal.dice)
            self.strategy = "failures"
            self.descriptor = "Rerolling Failures"

        elif strategy == "maximize_criticals":
            new_dice = _maximize_criticals(self.normal.dice)
            self.strategy = "criticals"
            self.descriptor = "Maximizing Criticals"

        elif strategy == "avoid_messy":
            new_dice = _avoid_messy(self.normal.dice)
            self.strategy = "messy"
            self.descriptor = "Avoiding Messy Critical"

        else: # strategy == "risky":
            new_dice = _risky_avoid_messy(self.normal.dice)
            self.strategy = "risky"
            self.descriptor = "Avoid Messy (Risky)"

        new_throw = DiceThrow(new_dice)
        self.normal = new_throw


def _reroll_failures(dice: list) -> list:
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


def _maximize_criticals(dice: list) -> list:
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
    total_failures = len([die for die in dice if die < 6])
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


def _avoid_messy(dice: list) -> list:
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


def _risky_avoid_messy(dice: list) -> list:
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
