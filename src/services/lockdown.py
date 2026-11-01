"""The bot's lockdown state, set ahead of a planned shutdown."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

import discord

LOCKDOWN_DELAY = timedelta(minutes=10)


class LockdownReason(StrEnum):
    """The potential reasons for a lockdown."""

    MAINTENANCE = "maintenance"
    UPDATE = "update"

    @property
    def phrase(self) -> str:
        """The reason as it reads after "going down for"."""
        return "an update" if self is LockdownReason.UPDATE else self.value


@dataclass(frozen=True)
class Lockdown:
    """Holds the bot's lockdown state: reason and rough shutdown time."""

    reason: LockdownReason
    shutdown_time: datetime

    def notice(self, bot_name: str) -> str:
        """Tell users why and when the bot is going down."""
        if self.shutdown_time > discord.utils.utcnow():
            when = discord.utils.format_dt(self.shutdown_time, "R")
        else:
            when = "shortly"
        return f"{bot_name} is going down for {self.reason.phrase} {when}."
