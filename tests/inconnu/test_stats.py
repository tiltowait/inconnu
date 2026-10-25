"""Tests for inconnu/stats.py."""

import pytest

import inconnu
from inconnu.stats import _gen_roll
from models import Impairment


@pytest.mark.parametrize(
    "penalty,impaired",
    [
        (Impairment.NONE, False),
        (Impairment.PHYSICAL, True),
        (Impairment.MENTAL, True),
        (Impairment.TOTAL, True),
    ],
)
def test_roll_entry_records_impairment(penalty: Impairment, impaired: bool):
    """Roll entries record whether an Impairment penalty was applied."""
    roll = inconnu.Roll(5, 0, 0, pool_str="Strength + Brawl", impairment_penalty=penalty)
    entry = _gen_roll(1, 2, 3, 4, None, roll, None)

    assert entry["impaired"] is impaired
