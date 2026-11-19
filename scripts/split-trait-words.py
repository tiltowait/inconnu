"""Split every character's traits and subtraits into multiword versions,
along with their macros and roll history. Dry run unless --commit is given.

Stop the bot and take a backup (mongodump) before committing.

Each character's rolls are rewritten before the character is saved. If the run
stops between the two, rerunning it rewrites the rest: the character still
has its old names, so the same renames are found, and rolls already rewritten
no longer match them."""

import asyncio
import json
import re
from argparse import ArgumentParser
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import NamedTuple, Self

from beanie import PydanticObjectId
from pymongo import UpdateOne

import db
from constants import ATTRIBUTES, DISCIPLINES, SKILLS, UNIVERSAL_TRAITS
from models import VChar
from models.vchardocs import VCharMacro, VCharTrait
from utils.text import split_words
from utils.validation import validate_specialty_names, validate_trait_names

ROLL_BATCH_SIZE = 1000

# Standard traits' names and types, keyed by casefolded name
STANDARD_TRAITS: dict[str, tuple[str, VCharTrait.Type]] = {
    name.casefold(): (name, trait_type)
    for names, trait_type in (
        (ATTRIBUTES, VCharTrait.Type.ATTRIBUTE),
        (SKILLS, VCharTrait.Type.SKILL),
        (DISCIPLINES, VCharTrait.Type.DISCIPLINE),
    )
    for name in names
}

# Inherent traits (Humanity, Hunger, ...) aren't stored with the others
INHERENT_TRAITS = {name.casefold() for name in UNIVERSAL_TRAITS}

type Validator = Callable[[str], None]
type NameMap = dict[str, str]  # Casefolded old name -> new name


class Arguments(NamedTuple):
    charid: PydanticObjectId | None
    commit: bool
    yes: bool
    log: Path

    @classmethod
    def parse(cls) -> Self:
        """Parse the CLI args."""
        parser = ArgumentParser(description=__doc__)
        parser.add_argument(
            "--charid",
            type=PydanticObjectId,
            help="Migrate only this character.",
        )
        parser.add_argument("--commit", action="store_true", help="Write the changes.")
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip the confirmation (for non-interactive shells).",
        )
        parser.add_argument(
            "--log",
            type=Path,
            default=Path("split-trait-words.jsonl"),
            help="Where to log each changed character (default: %(default)s).",
        )

        args = parser.parse_args()
        return cls(**vars(args))


@dataclass
class CharacterLog:
    """One changed character's renames, for the log."""

    charid: str
    name: str
    guild: int
    user: int
    traits: dict[str, str] = field(default_factory=dict)
    subtraits: dict[str, dict[str, str]] = field(default_factory=dict)
    types: dict[str, list[str]] = field(default_factory=dict)  # Name: [old, new]
    macros: dict[str, list[list[str]]] = field(default_factory=dict)  # Name: [old, new]
    rolls: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        """Whether anything changed."""
        return any((self.traits, self.subtraits, self.types, self.macros, self.rolls))


class Splitter:
    """Splits a character's trait and subtrait names into words, and maps its
    macros' pools and roll pools to match. A name keeps its original form if
    the split one is invalid or taken; each such name is recorded in problems.
    Standard traits get their standard names and types."""

    def __init__(self):
        self.problems: list[str] = []
        self.trait_names: NameMap = {}
        self.subtrait_names: dict[str, NameMap] = {}  # Keyed by casefolded old trait
        self.types: dict[str, list[str]] = {}  # New name: [old type, new type]

    def split_traits(self, traits: list[VCharTrait]) -> list[VCharTrait]:
        """Split the traits into multiword traits and subtraits, sorted as
        VChar and VCharTrait keep them."""
        names = self._rename([t.name for t in traits], validate_trait_names, "Trait")
        for trait, name in zip(traits, names):
            name = self._standardize(trait, name)

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

    def split_pool(self, pool: str) -> str:
        """Rename the traits and specialties in a roll's pool string, such as
        "-Strength + AnimalKen (BigCats, Dogs) - 1". Unknown names (numbers,
        deleted traits) are left alone. Call after split_traits()."""
        parts = re.split(r"( [+-] )", pool)
        return "".join(
            part if part in (" + ", " - ") else self._split_pool_operand(part) for part in parts
        )

    def _split_pool_operand(self, operand: str) -> str:
        """Rename a pool string operand: an optional minus sign, a trait, and
        optional specialties in parentheses."""
        match = re.fullmatch(r"(-?)(.*?)(?: \((.*)\))?", operand)
        if match is None:
            return operand

        sign, trait, specialties = match.groups()
        if (new_trait := self.trait_names.get(trait.casefold())) is None:
            return operand

        new_operand = sign + new_trait
        if specialties:
            subtrait_names = self.subtrait_names[trait.casefold()]
            renamed = [subtrait_names.get(s.casefold(), s) for s in specialties.split(", ")]
            new_operand += f" ({', '.join(renamed)})"

        return new_operand

    def _standardize(self, trait: VCharTrait, name: str) -> str:
        """Give a standard trait its standard name and type. Old characters
        (SPCs, especially) may have them as custom traits."""
        if (standard := STANDARD_TRAITS.get(name.casefold())) is None:
            return name

        standard_name, standard_type = standard
        if trait.type != standard_type:
            self.types[standard_name] = [trait.type, standard_type.value]
            if trait.raw_subtraits and standard_type == VCharTrait.Type.ATTRIBUTE:
                self.problems.append(f"Attribute `{standard_name}` has subtraits.")
            trait.type = standard_type.value

        return standard_name

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
        numbers, inherent traits, and anything unknown alone."""
        if token in ("+", "-") or token.isdigit():
            return token

        trait, *subtraits = token.split(".")
        if trait.casefold() in INHERENT_TRAITS:
            return token  # Not stored with the other traits, and never renamed
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


async def migrate(char: VChar, commit: bool) -> CharacterLog:
    """Split one character's names, macros, and roll pools, saving them if
    committing. Rolls are written before the character (see the module
    docstring)."""
    log = CharacterLog(charid=char.id_str, name=char.name, guild=char.guild, user=char.user)
    splitter = Splitter()

    old_traits = char.traits  # Deep copies
    old_macros = {macro.name: list(macro.pool) for macro in char.macros}

    try:
        new_traits = splitter.split_traits(char.traits)
    except RuntimeError as err:
        log.problems.append(f"Skipped: {err}")
        return log

    new_macros = splitter.split_macros(char.macros)
    log.problems = splitter.problems
    log.types = splitter.types

    # Record the renames
    for old in old_traits:
        new = splitter.trait_names[old.name.casefold()]
        if new != old.name:
            log.traits[old.name] = new
        subtraits = splitter.subtrait_names[old.name.casefold()]
        renamed = {s: subtraits[s.casefold()] for s in old.raw_subtraits}
        if changed := {old: new for old, new in renamed.items() if old != new}:
            log.subtraits[old.name] = changed
    for macro in new_macros:
        if macro.pool != old_macros[macro.name]:
            log.macros[macro.name] = [old_macros[macro.name], macro.pool]

    if not (log.traits or log.subtraits or log.types or log.macros):
        return log  # Nothing renamed, so rolls can't change, either

    log.rolls = await migrate_rolls(char.id, splitter, commit)

    if commit:
        char.raw_traits = new_traits
        char.macros = new_macros
        await char.save_changes()

    return log


async def migrate_rolls(charid: PydanticObjectId | None, splitter: Splitter, commit: bool) -> int:
    """Rewrite the character's roll pools. Returns how many changed."""
    count = 0
    updates: list[UpdateOne] = []
    query = {"charid": charid, "pool": {"$ne": None}}

    async for roll in db.rolls.find(query, {"pool": 1}):
        new_pool = splitter.split_pool(roll["pool"])
        if new_pool == roll["pool"]:
            continue

        count += 1
        if commit:
            updates.append(UpdateOne({"_id": roll["_id"]}, {"$set": {"pool": new_pool}}))
            if len(updates) >= ROLL_BATCH_SIZE:
                await db.rolls.bulk_write(updates, ordered=False)
                updates.clear()

    if updates:
        await db.rolls.bulk_write(updates, ordered=False)

    return count


def confirm(prompt: str) -> bool:
    """Ask a yes/no question. No input (a non-interactive shell) means no."""
    try:
        return input(prompt).lower() == "y"
    except EOFError:
        print()
        return False


async def main():
    args = Arguments.parse()
    await db.init()

    if args.charid is not None:
        query = VChar.find(VChar.id == args.charid)
    else:
        query = VChar.find_all()
    total = await query.count()

    if args.commit:
        print(f"This will migrate {total} character(s) and their rolls.")
        if not args.yes and not confirm("Is the bot stopped, and is there a backup? [y/n] "):
            print("Aborted.")
            return
    else:
        print(f"Dry run over {total} character(s). Nothing will be written.")

    changed = rolls = problems = 0
    with args.log.open("w") as log_file:
        async for char in query:
            log = await migrate(char, args.commit)
            if log.changed or log.problems:
                log_file.write(json.dumps(asdict(log)) + "\n")
            changed += log.changed
            rolls += log.rolls
            problems += len(log.problems)

    verb = "Migrated" if args.commit else "Would migrate"
    print(f"{verb} {changed} of {total} character(s) and {rolls} roll(s).")
    print(f"{problems} problem(s). Details: {args.log}")


if __name__ == "__main__":
    asyncio.run(main())
