"""Package-wide errors."""


class InconnuError(Exception):
    """Base error all others inherit from."""


class HandledError(InconnuError):
    """An error that needs no further handling."""


class RollError(InconnuError):
    """Base error pertaining to rolls."""


class HungerInPool(RollError):
    """An exception raised if Hunger is used in a roll pool."""


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


class MacroError(InconnuError):
    """Base macro error."""


class MacroAlreadyExistsError(MacroError):
    """Error for when a user tries to create a macro that already exists."""


class MacroNotFoundError(InconnuError):
    """Error for when a macro isn't found."""


class InvalidLogKeyError(InconnuError):
    """Error for when we try to modify an invalid log."""
