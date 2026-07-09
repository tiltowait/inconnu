"""Export all characters from a guild."""

import json
import os
import sys
from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path
from typing import NamedTuple, Self

from pymongo import MongoClient

MONGO_ENV = "INCONNU_MONGO"  # Change if necessary
MONGO_URL = os.getenv(MONGO_ENV)


class Arguments(NamedTuple):
    """Command-line arguments."""

    guild_id: int
    destination: Path

    @classmethod
    def parse(cls) -> Self:
        """Parse CLI arguments."""
        parser = ArgumentParser(description=__doc__)
        parser.add_argument("guild_id", type=int, help="The ID of the guild to export")
        parser.add_argument(
            "destination", type=cls._validate_destination, help="Where to save the JSON file"
        )

        args = parser.parse_args()
        return cls(**vars(args))

    @staticmethod
    def _validate_destination(destination: str) -> Path:
        """Validates and returns the destination path."""
        p = Path(destination)
        if p.suffix != ".json":
            raise ArgumentTypeError(f"Destination must end in .json (got {p.suffix}).")
        if not p.parent.exists():
            raise ArgumentTypeError(f"'{p.parent}' does not exist!")
        if p.exists():
            raise ArgumentTypeError(f"'{destination}' already exists!")

        return p


def main():
    if not MONGO_URL:
        sys.exit(f"'{MONGO_ENV}' not set!")

    args = Arguments.parse()

    with MongoClient(MONGO_URL) as client:
        db = client.get_database()
        guild_chars = list(db.characters.find({"guild": args.guild_id}))

    if not guild_chars:
        sys.exit(f"No characters found in {args.guild_id}!")

    with open(args.destination, "w") as f:
        json.dump(guild_chars, f, default=str, indent=2)

    print(f"Exported {len(guild_chars)} characters.")


if __name__ == "__main__":
    main()
