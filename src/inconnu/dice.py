"""Dice rolling utilities for Vampire: The Masquerade."""

from typing import overload

import pypcg

# PCG32 is better than Mersenne Twister
RNG = pypcg.PCG32()


@overload
def d10(count: None = None) -> int:
    pass


@overload
def d10(count: int) -> list[int]:
    pass


def d10(count: int | None = None) -> list[int] | int:
    """Generate one or a list of d10s."""
    if count is None:
        return RNG.randint(1, 10)
    return [RNG.randint(1, 10) for _ in range(count)]


def random(ceiling=100):
    """Get a random number between 1 and ceiling."""
    return RNG.randint(1, ceiling)
