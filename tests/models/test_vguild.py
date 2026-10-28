"""Tests for models/vguild.py."""

from datetime import datetime

from models import VGuild


def test_leave_marks_inactive():
    """Leaving records the date and marks the guild inactive, which culling requires."""
    vguild = VGuild(guild=1, name="Test Guild")
    vguild.leave()

    assert vguild.active is False
    assert isinstance(vguild.left, datetime)


def test_rejoin_marks_active():
    """Rejoining clears the leave, so the guild isn't culled."""
    vguild = VGuild(guild=1, name="Test Guild")
    vguild.leave()
    vguild.join()

    assert vguild.active is True
    assert vguild.left is None
