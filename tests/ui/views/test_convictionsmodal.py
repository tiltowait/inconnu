"""Tests for ui/views/convictionsmodal.py."""

from discord.ui import InputText

from constants import MAX_CONVICTION_LENGTH
from models import VChar
from ui.views import ConvictionsModal


def make_char(convictions: list[str]) -> VChar:
    """A character with the given Convictions."""
    return VChar(
        guild=1,
        user=2,
        name="Nadea",
        splat="vampire",
        humanity=7,
        health="......",
        willpower=".....",
        potency=1,
        convictions=convictions,
    )


async def test_conviction_limit():
    """Inputs leave room for the period the modal may add."""
    modal = ConvictionsModal(make_char(["Short."]))
    lengths = [item.max_length for item in modal.children if isinstance(item, InputText)]
    assert lengths == [MAX_CONVICTION_LENGTH - 1] * 3


async def test_conviction_limit_keeps_long_values():
    """A longer, older Conviction still fits, or the modal couldn't open."""
    long = "A" * 300
    modal = ConvictionsModal(make_char([long]))
    inputs = [item for item in modal.children if isinstance(item, InputText)]
    assert inputs[0].value == long
    assert inputs[0].max_length == 300
    assert inputs[1].max_length == MAX_CONVICTION_LENGTH - 1
