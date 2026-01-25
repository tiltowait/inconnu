"""Set up the package interface."""

from inconnu.traits.add_update import add, update
from inconnu.traits.delete import delete
from inconnu.traits.show import show
from inconnu.traits.show import traits_embed as embed
from inconnu.traits.traitcommon import validate_trait_names

__all__ = ("add", "delete", "embed", "show", "update", "validate_trait_names")
