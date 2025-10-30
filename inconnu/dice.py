"""Dice rolling utilities for Vampire: The Masquerade."""

from typing import overload

from numpy.random import default_rng

_rng = default_rng()


@overload
def d10(count: None = None) -> int:
    pass


@overload
def d10(count: int) -> list[int]:
    pass


def d10(count: int | None = None) -> list[int] | int:
    """Generate one or a list of d10s."""
    if count is None:
        return int(_rng.integers(1, 11))
    return list(map(int, _rng.integers(1, 11, count)))


def random(ceiling=100):
    """Get a random number between 1 and ceiling."""
    return _rng.integers(1, ceiling + 1)
