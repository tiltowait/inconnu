"""Split traits and subtraits into multiword versions."""

import asyncio
from argparse import ArgumentParser
from collections.abc import Callable
from typing import NamedTuple, Self

from beanie import PydanticObjectId

import db
from models import VChar
from models.vchardocs import VCharMacro, VCharTrait
from utils.text import split_words
from utils.validation import validate_specialty_names, validate_trait_names

type Validator = Callable[[str], None]
type NameMap = dict[str, str]  # Casefolded old name -> new name


class Arguments(NamedTuple):
    charid: PydanticObjectId

    @classmethod
    def parse(cls) -> Self:
        """Parse the CLI args."""
        parser = ArgumentParser(description=__doc__)
        parser.add_argument(
            "charid", type=PydanticObjectId, help="The ID of the character to modify."
        )

        args = parser.parse_args()
        return cls(**vars(args))


class Splitter:
    """Splits a character's trait and subtrait names into words, and maps its
    macros' pools to match. A name keeps its original form if the split one is
    invalid or taken; each such name is recorded in problems."""

    def __init__(self):
        self.problems: list[str] = []
        self.trait_names: NameMap = {}
        self.subtrait_names: dict[str, NameMap] = {}  # Keyed by casefolded old trait

    def split_traits(self, traits: list[VCharTrait]) -> list[VCharTrait]:
        """Split the traits into multiword traits and subtraits, sorted as
        VChar and VCharTrait keep them."""
        names = self._rename([t.name for t in traits], validate_trait_names, "Trait")
        for trait, name in zip(traits, names):
            label = f"{trait.name} subtrait"
            subtraits = self._rename(trait.raw_subtraits, validate_specialty_names, label)
            self.trait_names[trait.name.casefold()] = name
            self.subtrait_names[trait.name.casefold()] = {
                old.casefold(): new for old, new in zip(trait.raw_subtraits, subtraits)
            }

            trait.name = name
            trait.raw_subtraits = sorted(subtraits)  # VCharTrait._add_subtraits()'s order

        return sorted(traits, key=lambda t: t.name.casefold())  # VChar.assign_traits()'s order

    def split_macros(self, macros: list[VCharMacro]) -> list[VCharMacro]:
        """Rename the traits in the macros' pools. Call after split_traits()."""
        for macro in macros:
            macro.pool = [self._rename_operand(macro.name, token) for token in macro.pool]
        return macros

    def _rename(self, names: list[str], validator: Validator, label: str) -> list[str]:
        """Split each name into words. A name that would be invalid, or would
        duplicate another name in the list, keeps its original form."""
        candidates = [self._split(name, validator, label) for name in names]

        # Unchanged names keep priority, so a split name can't take theirs
        taken = {new.casefold() for old, new in zip(names, candidates) if old == new}
        renamed: list[str] = []

        for old, new in zip(names, candidates):
            if old != new:
                if new.casefold() in taken:
                    self.problems.append(f"Kept {label} `{old}`: `{new}` is taken.")
                    new = old
                    if new.casefold() in taken:
                        raise RuntimeError(f"Can't resolve {label} `{old}`; fix it by hand.")
                taken.add(new.casefold())
            renamed.append(new)

        return renamed

    def _split(self, name: str, validator: Validator, label: str) -> str:
        """Split a name into words, or return it unchanged if the result is
        invalid. Collapses the extra spaces stray underscores leave."""
        new = " ".join(split_words(name).split())
        if new == name:
            return name

        try:
            validator(new)
        except (SyntaxError, ValueError) as err:
            self.problems.append(f"Kept {label} `{name}`: {err}")
            return name

        return new

    def _rename_operand(self, macro: str, token: str) -> str:
        """Rename a macro pool token ("Trait.Subtrait"), leaving operators,
        numbers, and anything unknown alone."""
        if token in ("+", "-") or token.isdigit():
            return token

        trait, *subtraits = token.split(".")
        if (new_trait := self.trait_names.get(trait.casefold())) is None:
            self.problems.append(f"Macro `{macro}`: unknown trait `{trait}` left as-is.")
            return token

        subtrait_names = self.subtrait_names[trait.casefold()]
        new_subtraits = []
        for subtrait in subtraits:
            if (new_subtrait := subtrait_names.get(subtrait.casefold())) is None:
                self.problems.append(
                    f"Macro `{macro}`: unknown subtrait `{trait}.{subtrait}` left as-is."
                )
                new_subtrait = subtrait
            new_subtraits.append(new_subtrait)

        return ".".join([new_trait, *new_subtraits])


async def fetch_char(charid: PydanticObjectId) -> VChar:
    """Fetch the character by ID."""
    char = await VChar.find_one(VChar.id == charid)
    if not char:
        raise LookupError("Character not found.")
    return char


async def main():
    args = Arguments.parse()

    await db.init()
    char = await fetch_char(args.charid)
    print(f"Fetched: {char.name}\n")

    splitter = Splitter()
    char.raw_traits = splitter.split_traits(char.traits)  # char.traits deep copies
    char.macros = splitter.split_macros(char.macros)

    if splitter.problems:
        print("Problems:")
        for problem in splitter.problems:
            print(f"  {problem}")

    prompt = input("Save changes? [y/n] ")
    if prompt.lower() == "y":
        await char.save_changes()


if __name__ == "__main__":
    asyncio.run(main())
