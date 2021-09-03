"""exceptions.py - Character database exceptions."""

class CharacterNotFoundError(Exception):
    """Raised when a user specifies a nonexistent character."""
    pass

class TraitNotFoundError(Exception):
    """Raised when a user specifies a nonexistent trait."""
    pass

class AmbiguousTraitError(Exception):
    """Raised when a user's trait argument is ambiguous."""

    def __init__(self, input_trait, matches):
        self.input = input_trait
        self.matches = matches

        matches = map(lambda match: f"`{match}`", matches)
        formatted_matches = ", ".join(matches)
        self.message = f'`{input_trait}` is ambiguous. Do you mean: {formatted_matches}?'

        super().__init__(self.message)
