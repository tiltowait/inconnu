"""Tests for models/vchar.py."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from pymongo.asynchronous.collection import AsyncCollection

from constants import Damage
from models import BlushState, VChar
from models.vchar import Tracker
from models.vchardocs import VCharHeader
from tests.characters import gen_char


@pytest.mark.parametrize("old_blush", [BlushState.NA, BlushState.OFF])
def test_vampire_can_blush(old_blush: BlushState):
    """A vampire can Blush even if their header was set to N/A at Humanity 9+."""
    vamp = gen_char("vampire")
    vamp.header.blush = old_blush
    vamp.set_blush(BlushState.ON)

    assert vamp.header.blush == 1


@pytest.mark.parametrize("splat", ["mortal", "ghoul", "thin-blood"])
def test_non_vampire_cannot_blush(splat: str):
    """Only full vampires Blush."""
    char = gen_char(splat)
    char.header.blush = BlushState.NA
    char.set_blush(BlushState.ON)

    assert char.header.blush == -1


@pytest.mark.parametrize(
    "splat,can_blush,starting_blush",
    [
        ("vampire", True, 0),
        ("thin-blood", False, -1),
        ("ghoul", False, -1),
        ("mortal", False, -1),
    ],
)
def test_can_blush_sets_starting_blush(splat: str, can_blush: bool, starting_blush: int):
    """Only full vampires use the Blush of Life, so others start at N/A."""
    char = gen_char(splat)

    assert char.can_blush is can_blush
    assert char.header.blush == starting_blush


@pytest.mark.parametrize(
    "splat,humanity,expected",
    [("vampire", 7, 0), ("vampire", 9, -1), ("thin-blood", 7, -1), ("mortal", 7, -1)],
)
def test_reset_blush(splat: str, humanity: int, expected: int):
    """Those who can Blush turn it off; others become N/A."""
    char = gen_char(splat)
    char.humanity = humanity
    char.header.blush = BlushState.ON

    char.reset_blush()

    assert char.header.blush == expected


def test_not_equal_to_other_types():
    """Comparing to something that isn't a character doesn't raise."""
    assert gen_char("vampire") != "Nadea"


@pytest.mark.parametrize(
    "humanity,can_blush",
    [(7, True), (8, True), (9, False), (10, False)],
)
def test_can_blush_depends_on_humanity(humanity: int, can_blush: bool):
    """Vampires at Humanity 9+ don't Blush."""
    vamp = gen_char("vampire")
    vamp.humanity = humanity

    assert vamp.can_blush is can_blush


def test_can_blush_after_humanity_falls():
    """A vampire who falls below Humanity 9 can Blush despite an N/A header."""
    vamp = gen_char("vampire")
    vamp.humanity = 9
    vamp.header.blush = BlushState.NA
    vamp.humanity = 8

    vamp.set_blush(BlushState.ON)

    assert vamp.header.blush == 1


def test_high_humanity_cannot_set_blush():
    """Setting the Blush at Humanity 9+ is refused."""
    vamp = gen_char("vampire")
    vamp.humanity = 9
    vamp.header.blush = BlushState.NA

    vamp.set_blush(BlushState.ON)

    assert vamp.header.blush == -1


async def saved_blush(char: VChar) -> int:
    """Save the character and read its Blush back from the database."""
    await char.save()
    fresh = await VChar.get(char.id)
    assert fresh is not None
    await fresh.delete()
    return fresh.header.blush


@pytest.mark.parametrize("blush", [BlushState.OFF, BlushState.ON])
async def test_save_rising_to_high_humanity_clears_blush(blush: BlushState):
    """A vampire who no longer needs to Blush becomes N/A."""
    vamp = gen_char("vampire")
    await vamp.insert()
    vamp.header.blush = blush
    vamp.humanity = 9

    assert await saved_blush(vamp) == -1


async def test_save_falling_from_high_humanity_enables_blush():
    """A vampire who falls below Humanity 9 goes from N/A to Not Blushed."""
    vamp = gen_char("vampire")
    vamp.humanity = 9
    await vamp.insert()
    vamp.header.blush = BlushState.NA
    vamp.humanity = 8

    assert await saved_blush(vamp) == 0


async def test_save_keeps_active_blush():
    """A vampire who can Blush keeps their current status."""
    vamp = gen_char("vampire")
    await vamp.insert()
    vamp.header.blush = BlushState.ON

    assert await saved_blush(vamp) == 1


@pytest.mark.parametrize("splat", ["mortal", "ghoul", "thin-blood"])
async def test_save_after_splat_change_clears_blush(splat: str):
    """A character who stops being a full vampire becomes N/A."""
    vamp = gen_char("vampire")
    await vamp.insert()
    vamp.splat = splat

    assert await saved_blush(vamp) == -1


async def test_save_after_embrace_enables_blush():
    """A mortal who becomes a vampire goes from N/A to Not Blushed."""
    mortal = gen_char("mortal")
    await mortal.insert()
    mortal.splat = "vampire"

    assert await saved_blush(mortal) == 0


async def test_save_clears_stale_thin_blood_blush():
    """A Thin-Blood saved as Not Blushed by the old modal is corrected."""
    thin_blood = gen_char("thin-blood")
    await thin_blood.insert()
    thin_blood.header.blush = BlushState.OFF

    assert await saved_blush(thin_blood) == -1


@pytest.mark.parametrize(
    "new_lifetime,expected_lifetime,expected_unspent",
    [
        (30, 30, 15),  # Raising lifetime raises unspent by as much
        (15, 15, 0),  # Lowering it lowers unspent by as much
        (10, 10, -5),  # Unspent may go negative
        (-5, 0, -15),  # Lifetime stops at zero, and unspent drops by the real change
    ],
)
def test_set_lifetime_xp(new_lifetime: int, expected_lifetime: int, expected_unspent: int):
    """Lifetime XP changes move unspent XP by the same amount."""
    char = gen_char("vampire")
    char.experience.lifetime = 20
    char.experience.unspent = 5

    char.set_lifetime_xp(new_lifetime)

    assert char.experience.lifetime == expected_lifetime
    assert char.experience.unspent == expected_unspent


@pytest.mark.parametrize(
    "amount,scope,event,expected_unspent,expected_lifetime",
    [
        (5, "unspent", "award_unspent", 10, 20),
        (-3, "unspent", "deduct_unspent", 2, 20),
        (5, "lifetime", "award_lifetime", 10, 25),
        (-3, "lifetime", "deduct_lifetime", 2, 17),
    ],
)
def test_apply_experience(
    amount: int, scope: str, event: str, expected_unspent: int, expected_lifetime: int
):
    """Experience changes update the totals and are logged."""
    char = gen_char("vampire")
    char.experience.unspent = 5
    char.experience.lifetime = 20

    char.apply_experience(amount, scope, "Reason", 123)

    assert char.experience.unspent == expected_unspent
    assert char.experience.lifetime == expected_lifetime
    assert len(char.experience.log) == 1
    entry = char.experience.log[0]
    assert (entry.event, entry.amount, entry.reason, entry.admin) == (event, amount, "Reason", 123)


def test_apply_experience_ignores_zero():
    """Zero-XP changes aren't logged."""
    char = gen_char("vampire")
    char.apply_experience(0, "lifetime", "Nothing", 123)

    assert char.experience.lifetime == 0
    assert not char.experience.log


def test_header_without_blush_loads_as_off():
    """Characters predating the Blush field have no stored value."""
    assert VCharHeader.model_validate({"location": "Elysium"}).blush is BlushState.OFF


@pytest.mark.parametrize("stored", [-1, 0, 1])
def test_stored_blush_loads_as_enum(stored: int):
    """Integers in the database become BlushStates."""
    assert VCharHeader.model_validate({"blush": stored}).blush is BlushState(stored)


def test_damage_taken_is_counted():
    """Damage taken is counted per tracker and severity."""
    char = gen_char("vampire")
    char.set_damage(Tracker.HEALTH, Damage.SUPERFICIAL, 2)
    char.set_damage(Tracker.WILLPOWER, Damage.AGGRAVATED, 1)

    log = char.log
    assert (log.health_superficial, log.health_aggravated) == (2, 0)
    assert (log.willpower_superficial, log.willpower_aggravated) == (0, 1)


def test_healing_is_not_counted():
    """Healing leaves the damage counts alone."""
    char = gen_char("vampire")
    char.set_damage(Tracker.HEALTH, Damage.SUPERFICIAL, 3)
    char.set_damage(Tracker.HEALTH, Damage.SUPERFICIAL, 1)

    assert char.log.health_superficial == 3


@pytest.mark.parametrize(
    "track,severity",
    [
        ("....", 0),
        ("../x", 13),
        ("//xx", 26),
    ],
)
def test_damage_severity(track: str, severity: int):
    """Superficial damage is worth 3; Aggravated, 10."""
    assert VChar.damage_severity(track) == severity


def test_worst_damage_is_kept():
    """The worst track survives healing and lighter damage, per tracker."""
    char = gen_char("vampire")
    char.health = "." * 8
    char.set_damage(Tracker.HEALTH, Damage.SUPERFICIAL, 4)  # 12
    char.set_damage(Tracker.HEALTH, Damage.SUPERFICIAL, 0)
    char.set_damage(Tracker.HEALTH, Damage.AGGRAVATED, 1)  # 10
    char.set_damage(Tracker.WILLPOWER, Damage.SUPERFICIAL, 1)

    assert char.log.worst_health == "....////"
    assert char.log.worst_willpower == char.willpower


def test_worse_damage_replaces_worst():
    """Heavier damage replaces the stored track."""
    char = gen_char("vampire")
    char.health = "." * 8
    char.set_damage(Tracker.HEALTH, Damage.SUPERFICIAL, 3)  # 9
    char.set_damage(Tracker.HEALTH, Damage.SUPERFICIAL, 0)
    char.set_damage(Tracker.HEALTH, Damage.AGGRAVATED, 1)  # 10

    assert char.log.worst_health == ".......x"


@pytest.fixture
async def stored_char() -> AsyncGenerator[VChar]:
    """A character in the database, as the bot would load it."""
    char = gen_char("vampire")
    await char.insert()
    yield char
    await char.delete()


def characters() -> AsyncCollection:
    """The raw characters collection, for changes the document doesn't see."""
    return VChar.get_pymongo_collection()


async def test_save_changes_writes_only_changes(stored_char: VChar):
    """Saving changes leaves fields changed elsewhere alone."""
    await characters().update_one({"_id": stored_char.id}, {"$set": {"name": "Renamed"}})
    stored_char.hunger = 3
    await stored_char.save_changes()

    stored = await characters().find_one({"_id": stored_char.id})
    assert stored is not None
    assert (stored["name"], stored["hunger"]) == ("Renamed", 3)


async def test_returning_owner_is_not_culled(stored_char: VChar):
    """Clearing the departure date stores it, so culling skips the character."""
    stored_char.log.left = datetime.now(UTC) - timedelta(days=60)
    await stored_char.save_changes()
    stored_char.log.left = None
    await stored_char.save_changes()

    culled = {"_id": stored_char.id, "log.left": {"$lt": datetime.now(UTC) - timedelta(days=30)}}
    assert await characters().find_one(culled) is None
