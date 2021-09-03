"""roll.py - Perform a pool-based roll with hunger and difficulty."""

from .dicethrow import DiceThrow
from .rollresult import RollResult

def roll(parameters):
    """Perform a roll."""
    pool = parameters.pool
    hunger = parameters.hunger
    difficulty = parameters.difficulty

    normal_dice = pool - hunger
    if normal_dice < 0:
        normal_dice = 0

    normal_dice = DiceThrow(normal_dice)
    hunger_dice = DiceThrow(hunger)

    return RollResult(normal_dice, hunger_dice, difficulty)
