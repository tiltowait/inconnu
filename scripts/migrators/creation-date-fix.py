"""Add a creation date to characters that don't have one.
This script exists due to a bug in the Beanie docs: Document.save() does NOT
actually trigger Insert events if the document is new."""

from argparse import ArgumentParser

from bson import ObjectId
from pymongo import MongoClient, UpdateOne


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mongo_url", help="The Mongo connection string to use")
    parser.add_argument("db", help="The database to use")
    parser.add_argument("--commit", action="store_true", help="Actually commit the db writes.")
    args = parser.parse_args()

    client = MongoClient(args.mongo_url)
    try:
        db = client[args.db]

        updates: list[UpdateOne] = []
        for missing in db.characters.find({"log.created": {"$exists": False}}, {"_id": 1}):
            oid: ObjectId = missing["_id"]
            updates.append(UpdateOne({"_id": oid}, {"$set": {"log.created": oid.generation_time}}))

        if not updates:
            print("No characters need updating.")
            return

        if not args.commit:
            print(f"This operation would update {len(updates)} characters.")
        else:
            with client.start_session() as session:
                with session.start_transaction():
                    res = db.characters.bulk_write(updates, session=session)
                    print(f"Updated {res.modified_count} characters.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
