"""Print the number of characters created by /character wizard."""

import os
from datetime import UTC, datetime

from pymongo import MongoClient


def main():
    client = MongoClient(os.environ["INCONNU_MONGO"])
    db = client.prod

    date = datetime(2026, 2, 8, 3, 9, tzinfo=UTC)
    count = db.characters.count_documents({"log.created": {"$gte": date}})
    print(count)


if __name__ == "__main__":
    main()
