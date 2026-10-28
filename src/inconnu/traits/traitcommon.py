"""traits/traitcommon.py - Common functionality across trait operations."""

from collections.abc import Callable

import errors
from models import VChar
from utils.validation import VALID_TRAIT_PATTERN, validate_trait_names

__all__ = (
    "VALID_TRAIT_PATTERN",
    "any_trait_filter",
    "missing_traits_message",
    "validate_trait_names",
)


def any_trait_filter(*names: str) -> Callable[[VChar], None]:
    """A Haven filter that passes characters having at least one of the named traits."""

    def char_filter(character: VChar):
        """Raise a TraitError if the character has none of the traits."""
        if not any(character.has_trait(name) for name in names):
            if len(names) == 1:
                raise errors.TraitNotFound(character, names[0])
            raise errors.TraitError(f"{character.name} has none of these traits: {_join(names)}.")

    return char_filter


def missing_traits_message(*names: str) -> str:
    """The Haven error for when none of the user's characters have the traits."""
    if len(names) == 1:
        return f"None of your characters have a trait named `{names[0]}`."
    return f"None of your characters have any of these traits: {_join(names)}."


def _join(names: tuple[str, ...]) -> str:
    """Join trait names into a backticked list."""
    return ", ".join(f"`{name}`" for name in names)
