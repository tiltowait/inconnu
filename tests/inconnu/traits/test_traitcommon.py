"""Tests for traits/traitcommon.py."""

import pytest

import errors
import tests.characters
from inconnu.traits.traitcommon import any_trait_filter, missing_traits_message


def test_any_trait_filter_passes_with_one_owned_trait():
    """A character owning any of the traits passes."""
    char = tests.characters.gen_char("vampire")
    char.assign_traits({"Custom": 2})

    any_trait_filter("Missing", "custom")(char)


@pytest.mark.parametrize(
    "names,message",
    [
        (("Missing",), "{} has no trait named `Missing`."),
        (("Missing", "Other"), "{} has none of these traits: `Missing`, `Other`."),
    ],
)
def test_any_trait_filter_rejects_without_owned_traits(names: tuple[str, ...], message: str):
    """A character owning none of the traits is rejected."""
    char = tests.characters.gen_char("vampire")
    char.assign_traits({"Custom": 2})

    with pytest.raises(errors.TraitError) as err:
        any_trait_filter(*names)(char)

    assert str(err.value) == message.format(char.name)


@pytest.mark.parametrize(
    "names,message",
    [
        (("Foo",), "None of your characters have a trait named `Foo`."),
        (("Foo", "Bar"), "None of your characters have any of these traits: `Foo`, `Bar`."),
    ],
)
def test_missing_traits_message(names: tuple[str, ...], message: str):
    """The message names every trait."""
    assert missing_traits_message(*names) == message
