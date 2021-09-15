"""roll.py - Perform a pool-based roll with hunger and difficulty."""

from .dicethrow import DiceThrow
from .rollresult import RollResult

def roll_pool(parameters, pool_str=None):
    """Perform a roll."""
    if parameters.pool > 50:
        raise ValueError(f"Pool cannot exceed 50. (Got {parameters.pool}.)")
    if parameters.pool < 1:
        raise ValueError(f"Pool must be 1 or greater. (Got {parameters.pool}.)")

    pool = parameters.pool
    hunger = parameters.hunger
    difficulty = parameters.difficulty

    normal_dice = pool - hunger
    if normal_dice < 0:
        normal_dice = 0

    normal_dice = DiceThrow(normal_dice)
    hunger_dice = DiceThrow(hunger)

    outcome = RollResult(normal_dice, hunger_dice, difficulty)
    if pool_str is not None and not pool_str.isdigit():
        outcome.pool_str = pool_str

    return outcome
