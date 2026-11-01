"""Tests for services/lockdown.py."""

from datetime import timedelta

import discord
import pytest

from services.lockdown import Lockdown, LockdownReason


@pytest.mark.parametrize(
    "reason,phrase",
    [(LockdownReason.MAINTENANCE, "maintenance"), (LockdownReason.UPDATE, "an update")],
)
def test_notice(reason: LockdownReason, phrase: str):
    """The notice gives the reason and the time until shutdown."""
    shutdown_time = discord.utils.utcnow() + timedelta(minutes=5)
    lockdown = Lockdown(reason, shutdown_time)

    when = discord.utils.format_dt(shutdown_time, "R")
    assert lockdown.notice("Inconnu") == f"Inconnu is going down for {phrase} {when}."


def test_notice_after_shutdown_time():
    """Once the shutdown time passes, the notice says it's coming shortly."""
    lockdown = Lockdown(LockdownReason.UPDATE, discord.utils.utcnow() - timedelta(minutes=1))
    assert lockdown.notice("Inconnu") == "Inconnu is going down for an update shortly."
