"""Package-wide errors."""

from discord.ext import commands
from discord.ext.commands import CheckFailure


class NotPremium(commands.CommandError):
    """Error for users who are not premium supporters."""


class LockdownError(CheckFailure):
    """An exception raised if the bot is on lockdown."""


class InconnuError(Exception):
    """Base error all others inherit from."""


class NotReady(commands.CommandError):
    """An exception for when the bot hasn't fully loaded yet."""


class FetchError(Exception):
    """Generic character fetch error."""


class HandledError(InconnuError):
    """An error that needs no further handling."""


class RollError(InconnuError):
    """Base error pertaining to rolls."""


class WebhookError(InconnuError):
    """Error when a webhook can't be created."""


class HungerInPool(RollError):
    """An exception raised if Hunger is used in a roll pool."""


class TooManyParameters(RollError):
    """An exception raised if too many roll parameters are given."""

    def __init__(self, count: int, message: str):
        self.count = count
        super().__init__(message)


# Character Errors


class CharacterError(InconnuError):
    """Raised when there is an issue fetching a character."""


class NoCharactersError(CharacterError):
    """Raised when the user has no characters."""


class UnspecifiedCharacterError(CharacterError):
    """Raised when the user needs to specify a character but hasn't."""


class CharacterNotFoundError(CharacterError):
    """Raised when a given character does not exist."""


class TraitError(InconnuError):
    """Base error class for trait errors."""


class TraitAlreadyExistsError(TraitError):
    """Raised when the user tries to add an extant trait."""


class TraitNotFoundError(TraitError):
    """Raised when a user specifies a nonexistent trait."""

    def __init__(self, character, trait: str):
        super().__init__()
        self.name = character.name
        self.trait = trait

    def __str__(self) -> str:
        return f"{self.name} has no trait named `{self.trait}`."


class AmbiguousTraitError(TraitError):
    """Raised when a user's trait argument is ambiguous."""

    def __init__(self, input_trait, matches):
        self.input = input_trait
        self.matches = matches

        matches = map(lambda match: f"`{match}`", matches)
        formatted_matches = ", ".join(matches)
        self.message = f"`{input_trait}` is ambiguous. Do you mean: {formatted_matches}?"

        super().__init__(self.message)


class SpecialtiesNotAllowed(TraitError):
    """Raised when a trait can't have a specialty."""


class MacroError(InconnuError):
    """Base macro error."""


class MacroAlreadyExistsError(MacroError):
    """Error for when a user tries to create a macro that already exists."""


class MacroNotFoundError(InconnuError):
    """Error for when a macro isn't found."""


class InvalidLogKeyError(InconnuError):
    """Error for when we try to modify an invalid log."""
