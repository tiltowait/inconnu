"""Copy a character to the test database."""

import os
from argparse import ArgumentParser
from typing import Any

from bson import ObjectId
from pymongo import MongoClient

type Character = dict[str, Any]

TEST_GUILD = 826628660450689074
TEST_USER = 229736753676681230


def fetch_char(char_id: ObjectId) -> Character:
    """Fetch a character by ID."""
    client = MongoClient(os.environ["INCONNU_MONGO"])
    db = client.prod

    char = db.characters.find_one({"_id": char_id})
    if char is None:
        raise ValueError("Character not found")
    return char


def copy_char(char: Character):
    """Copy the character to the test database."""
    client = MongoClient(os.environ["INCONNU_DEV"])
    db = client.dev

    char["guild"] = TEST_GUILD
    char["user"] = TEST_USER
    db.characters.insert_one(char)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("char_id", help="The character ID to copy to the test server")
    args = parser.parse_args()

    if not ObjectId.is_valid(args.char_id):
        parser.error("Character ID must be a valid ObjectId.")

    char_id = ObjectId(args.char_id)
    char = fetch_char(char_id)

    print(f"Fetched {char['name']}")
    copy_char(char)
    print(f"Copied {char['name']} to dev server")


if __name__ == "__main__":
    main()
