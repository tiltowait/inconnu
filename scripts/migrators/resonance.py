"""Migrate guilds to new Resonance setting data type."""

import os
import sys
from argparse import ArgumentParser
from functools import partial
from typing import Literal, NamedTuple, Self

from pymongo import MongoClient

from models import ResonanceMode

flush = partial(print, end=" ... ", flush=True)

ADD_EMPTY_KEY = "settings.add_empty_resonance"
NEW_RESONANCE_KEY = "settings.resonance"


class Arguments(NamedTuple):
    env: Literal["prod", "dev"]

    @classmethod
    def parse(cls) -> Self:
        """Parse the arguments."""
        parser = ArgumentParser(description=__doc__)
        parser.add_argument(
            "env", choices=["prod", "dev"], help="The environment on which to work."
        )
        args = parser.parse_args()
        return cls(**vars(args))


def yorn(prompt: str) -> bool:
    """Present a yes/no prompt."""
    while True:
        answer = input(f"{prompt} Continue? [y/n] ")
        if answer.lower() == "y":
            return True
        elif answer.lower() == "n":
            return False


def main():
    args = Arguments.parse()
    if args.env == "dev":
        client = MongoClient(os.environ["INCONNU_DEV"])
        db = client.dev
    else:
        client = MongoClient(os.environ["INCONNU_MONGO"])
        db = client.prod

    count = db.guilds.count_documents({})
    if not yorn(f"This will impact {count} guilds."):
        sys.exit("Canceling")
    if args.env == "prod" and not yorn(f"THIS WILL AFFECT PROD!"):
        sys.exit("Canceling")

    with client.start_session() as session:
        with session.start_transaction():
            flush("Setting 'add_empty'")
            db.guilds.update_many(
                {ADD_EMPTY_KEY: True},
                {"$set": {NEW_RESONANCE_KEY: ResonanceMode.ADD_EMPTY.value}},
                session=session,
            )
            print("done!")

            flush("Setting 'standard'")
            db.guilds.update_many(
                {ADD_EMPTY_KEY: {"$ne": True}},
                {"$set": {NEW_RESONANCE_KEY: ResonanceMode.STANDARD.value}},
                session=session,
            )
            print("done!")

            flush("Removing settings.add_empty_resonance")
            db.guilds.update_many(
                {},
                {"$unset": {ADD_EMPTY_KEY: 1}},
                session=session,
            )
            print("done!")


if __name__ == "__main__":
    main()
