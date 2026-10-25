"""strategy.py - Willpower reroll strategies."""

from enum import StrEnum


class Strategy(StrEnum):
    """A Willpower reroll strategy."""

    REROLL_FAILURES = "reroll_failures"
    MAXIMIZE_CRITICALS = "maximize_criticals"
    AVOID_MESSY = "avoid_messy"
    RISKY = "risky"

    @property
    def description(self) -> str:
        """The strategy's display name."""
        match self:
            case Strategy.REROLL_FAILURES:
                return "Re-rolling Failures"
            case Strategy.MAXIMIZE_CRITICALS:
                return "Maximizing Crits"
            case Strategy.AVOID_MESSY:
                return "Avoiding Messy Crits"
            case Strategy.RISKY:
                return "Riskily Avoiding Messy Crits"
