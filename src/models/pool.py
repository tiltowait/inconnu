"""models/pool.py - Pool strings, as rolls log them: "Strength + Animal Ken
(Big Cats) - 1"."""

import re
from collections.abc import Iterable
from typing import NamedTuple


class PoolOperand(NamedTuple):
    """One operand of a pool string, such as "-Animal Ken (Big Cats, Dogs)"."""

    sign: str  # "-" when the pool starts by subtracting it; otherwise ""
    name: str
    specialties: str | None  # As written between the parentheses

    def __str__(self) -> str:
        """The operand as written in the pool string."""
        operand = self.sign + self.name
        if self.specialties is not None:
            operand += f" ({self.specialties})"
        return operand


type PoolPart = str | PoolOperand  # An operand, or the " + "/" - " between two


def split_pool(pool: str) -> list[PoolPart]:
    """Split a pool string, such as "Strength + Animal Ken (Big Cats) - 1",
    into its operands and the operators between them. Names have spaces, so
    we split on the operators. join_pool() reverses it."""
    parts: list[PoolPart] = []
    for part in re.split(r"( [+-] )", pool):
        if part in (" + ", " - "):
            parts.append(part)
            continue

        sign = "-" if part.startswith("-") else ""
        name, paren, specialties = part.removeprefix("-").partition(" (")
        parts.append(PoolOperand(sign, name, specialties.removesuffix(")") if paren else None))

    return parts


def join_pool(parts: Iterable[PoolPart]) -> str:
    """Join split_pool()'s parts back into a pool string."""
    return "".join(map(str, parts))


def pool_traits(pool: str) -> set[str]:
    """The trait names in a pool string, such as "Strength + Animal Ken (Big
    Cats) - 1": {"Strength", "Animal Ken", "1"}, without specialties or minus
    signs."""
    return {part.name for part in split_pool(pool) if isinstance(part, PoolOperand)}
