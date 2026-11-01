"""Reset the changelog flag in the dev environment."""

import os

from pymongo import MongoClient

DB_ENV_VAR = "INCONNU_DEV"
FIELD = "last_version_used"
UNSET_VALUE = ""


def main():
    client = MongoClient(os.environ[DB_ENV_VAR])
    db = client.dev

    print(f"Setting {FIELD} to {UNSET_VALUE!r} on {DB_ENV_VAR}", end=" ... ", flush=True)
    result = db.users.update_many({}, {"$set": {FIELD: UNSET_VALUE}})
    print(f"{result.modified_count} users reset.")


if __name__ == "__main__":
    main()
