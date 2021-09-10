"""exceptions.py - Character database exceptions."""

class CharacterError(Exception):
    """Raised when there is an issue fetching a character."""

class TraitAlreadyExistsError(Exception):
    """Raised when the user tries to add an extant trait."""

class TraitNotFoundError(Exception):
    """Raised when a user specifies a nonexistent trait."""

class AmbiguousTraitError(Exception):
    """Raised when a user's trait argument is ambiguous."""

    def __init__(self, input_trait, matches):
        self.input = input_trait
        self.matches = matches

        matches = map(lambda match: f"`{match}`", matches)
        formatted_matches = ", ".join(matches)
        self.message = f'`{input_trait}` is ambiguous. Do you mean: {formatted_matches}?'

        super().__init__(self.message)


class MacroAlreadyExistsError(Exception):
    """Error for when a user tries to create a macro that already exists."""

class MacroNotFoundError(Exception):
    """Error for when a macro isn't found."""
