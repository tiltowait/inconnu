"""Tests for models/vguild.py."""

from datetime import datetime
from unittest.mock import MagicMock

import discord

from models import VGuild

GUILD_ID = 1123581321


async def fetch_new_guild() -> VGuild:
    """A newly created guild, fetched as the bot would."""
    VGuild.get_or_fetch.cache_clear()
    await VGuild.find({"guild": GUILD_ID}).delete()

    guild = MagicMock(spec=discord.Guild, id=GUILD_ID)
    guild.name = "Test Guild"
    return await VGuild.get_or_fetch(guild)


async def saved_guild() -> VGuild:
    """The guild as stored."""
    vguild = await VGuild.find_one({"guild": GUILD_ID})
    assert vguild is not None
    return vguild


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


async def test_saves_setting_changes():
    """Saving changes stores changed settings, including lists."""
    vguild = await fetch_new_guild()
    vguild.settings.max_hunger = 7
    vguild.settings.oblivion_stains = [10]
    await vguild.save_changes()

    saved = await saved_guild()
    assert saved.settings.max_hunger == 7
    assert saved.settings.oblivion_stains == [10]


async def test_saves_cleared_fields():
    """Saving changes stores fields set back to None."""
    vguild = await fetch_new_guild()
    vguild.leave()
    await vguild.save_changes()
    vguild.join()
    await vguild.save_changes()

    saved = await saved_guild()
    assert saved.active is True
    assert saved.left is None
