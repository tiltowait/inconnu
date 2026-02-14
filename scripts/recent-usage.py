"""Recent bot usage data."""

import os
from datetime import UTC, datetime, timedelta

from pymongo import MongoClient

LOCAL_TZ = "America/Los_Angeles"


def main():
    client = MongoClient(os.environ["INCONNU_MONGO"])
    db = client.prod

    period = datetime.now(UTC) - timedelta(hours=8)
    pipeline = [
        {"$match": {"date": {"$gte": period}}},
        {
            "$group": {
                "_id": {"$hour": {"date": "$date", "timezone": LOCAL_TZ}},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": -1}},
    ]
    hour_counts = list(db.command_log.aggregate(pipeline))

    print("HOUR\tCOMMANDS")
    print("----\t-------")
    for count in hour_counts:
        print(f"{count['_id']:4d}\t{count['count']}")


if __name__ == "__main__":
    main()
