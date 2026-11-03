"""Tests for inconnu/experience/list.py."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import discord

import inconnu.experience.list as list_module
from models.vchardocs import VCharExperienceEntry
from tests.characters import gen_char

type MockMember = MagicMock

get_chunks = getattr(list_module, "__get_chunks")
get_embeds = getattr(list_module, "__get_embeds")


def _entry(reason: str, amount: int = 5, event: str = "award_lifetime") -> VCharExperienceEntry:
    """A log entry made at a fixed time."""
    return VCharExperienceEntry(
        event=event, amount=amount, reason=reason, admin=99, date=datetime(2026, 1, 2, tzinfo=UTC)
    )


async def test_empty_log():
    """A character without entries gets a placeholder."""
    chunks = await get_chunks(gen_char("vampire"))

    assert len(chunks.pages) == 1
    assert "No experience awards/deductions" in chunks.pages[0]


async def test_entries_newest_first():
    """Entries are numbered newest first, matching /experience remove entry."""
    char = gen_char("vampire")
    char.experience.log = [
        _entry("Old"),
        _entry("New", amount=-3, event="deduct_unspent"),
    ]

    lines = (await get_chunks(char)).pages[0].strip().split("\n")

    date = discord.utils.format_dt(datetime(2026, 1, 2, tzinfo=UTC), "d")
    assert lines == [
        f"1. **-3 unspent: New** - <@99> • {date}",
        f"2. **+5 lifetime: Old** - <@99> • {date}",
    ]


async def test_long_log_pages():
    """Long logs are split across pages."""
    char = gen_char("vampire")
    char.experience.log = [_entry("x" * 190) for _ in range(30)]

    chunks = await get_chunks(char)

    assert len(chunks.pages) > 1
    assert all(len(page) <= 2000 for page in chunks.pages)


async def test_embeds_show_totals():
    """Each page shows the character's current totals."""
    char = gen_char("vampire")
    char.experience.unspent = 4
    char.experience.lifetime = 9
    char.experience.log = [_entry("x" * 190) for _ in range(30)]
    player: MockMember = MagicMock(spec=discord.Member)

    embeds = await get_embeds(char, player)

    assert len(embeds) > 1
    for embed in embeds:
        assert embed.author.name == char.name
        assert embed.fields[0].value == "```4 / 9```"
