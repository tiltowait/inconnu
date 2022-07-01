"""dicethrow.py - A class for tracking dice throws."""

import inconnu


class DiceThrow:
    """Roll a specified number of dice and allow the user to query its statistics."""

    def __init__(self, dice):
        if isinstance(dice, int):
            self.dice = inconnu.d10(dice)
        else:
            self.dice = dice

    @property
    def count(self):
        """The number of rolled dice."""
        return len(self.dice)

    @property
    def ones(self):
        """Retrieve the number of ones in the dice."""
        return self.dice.count(1)

    @property
    def failures(self):
        """Retrieve the number of unsuccessful dice."""
        return self.__count_in_range(1, 5)

    @property
    def successes(self):
        """Retrieve the number of dice with 6 or higher."""
        return self.__count_in_range(6, 10)

    @property
    def tens(self):
        """Retrieve the number of rolled tens."""
        return self.dice.count(10)

    def __count_in_range(self, minimum, maximum):
        """Return the number of dice within the specified range. (Inclusive.)"""
        count = 0
        for die in self.dice:
            if minimum <= die <= maximum:
                count += 1

        return count
