"""Set Blush to N/A on characters who can't Blush.

Matches VChar.can_blush: only full vampires below Humanity 9 can. Without --apply,
this only reports what would change. Uses the dev database unless given --prod.

The bot caches characters and saves whole documents, so stop it first. Otherwise,
it could overwrite these changes.
"""

import argparse
import os
from collections import Counter

from pymongo import MongoClient
from pymongo.collection import Collection

NA = -1
MIN_UNBLUSHING_HUMANITY = 9
QUERY = {
    "header.blush": {"$ne": NA},
    "$or": [
        {"splat": {"$ne": "vampire"}},
        {"humanity": {"$gte": MIN_UNBLUSHING_HUMANITY}},
    ],
}


def summarize(characters: Collection) -> Counter[str]:
    """Count the characters who would change, by splat and Humanity."""
    counts = Counter()
    for char in characters.find(QUERY, {"splat": 1, "humanity": 1}):
        humanity = char.get("humanity", 0)
        high_humanity = " (Humanity 9+)" if humanity >= MIN_UNBLUSHING_HUMANITY else ""
        counts[f"{char.get('splat')}{high_humanity}"] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description="Set Blush to N/A on characters who can't Blush.")
    parser.add_argument("--apply", action="store_true", help="Save the changes")
    parser.add_argument("--prod", action="store_true", help="Use the production database")
    args = parser.parse_args()

    if args.prod:
        db = MongoClient(os.environ["INCONNU_MONGO"]).prod
    else:
        db = MongoClient(os.environ["INCONNU_DEV"]).dev
    characters = db.characters

    print(f"Database: {db.name}")

    counts = summarize(characters)
    for group, count in sorted(counts.items()):
        print(f"{group}: {count}")
    print(f"Total: {counts.total()}")

    if args.apply:
        result = characters.update_many(QUERY, {"$set": {"header.blush": NA}})
        print(f"Updated {result.modified_count} characters.")
    else:
        print("Dry run; nothing changed. Use --apply to save.")


if __name__ == "__main__":
    main()
