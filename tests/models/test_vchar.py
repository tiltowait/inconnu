"""Tests for models/vchar.py."""

import pytest

from tests.characters import gen_char


@pytest.mark.parametrize("old_blush", [-1, 0])
def test_vampire_can_blush(old_blush: int):
    """A vampire can Blush even if their header was set to N/A at Humanity 9+."""
    vamp = gen_char("vampire")
    vamp.header.blush = old_blush
    vamp.set_blush(1)

    assert vamp.header.blush == 1


@pytest.mark.parametrize("splat", ["mortal", "ghoul", "thin-blood"])
def test_non_vampire_cannot_blush(splat: str):
    """Only full vampires Blush."""
    char = gen_char(splat)
    char.header.blush = -1
    char.set_blush(1)

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
    vamp.header.blush = -1
    vamp.humanity = 8

    vamp.set_blush(1)

    assert vamp.header.blush == 1


def test_high_humanity_cannot_set_blush():
    """Setting the Blush at Humanity 9+ is refused."""
    vamp = gen_char("vampire")
    vamp.humanity = 9
    vamp.header.blush = -1

    vamp.set_blush(1)

    assert vamp.header.blush == -1


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
