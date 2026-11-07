"""Benchmark /statistics against the character with the most rolls.

Finds the character with the most rolls counted in statistics, then times the
Traits and General pipelines. Read-only. Uses the dev database unless given
--prod.

The pipelines are copies of those in inconnu/reference/statistics.py, so keep
them in sync. General covers all of the owner's characters on the server, so it
can scan more rolls than the top character has.
"""

import argparse
import os
import statistics
from collections.abc import Callable
from datetime import datetime
from time import perf_counter
from typing import Any

from bson import ObjectId
from pymongo import MongoClient
from pymongo.database import Database

DEADLINE = 3.0  # Discord's limit for an initial response, in seconds
DEFAULT_DATE = "19700101"  # The /statistics default

type Pipeline = list[dict[str, Any]]


def find_top_character(db: Database) -> tuple[ObjectId, int]:
    """Find the character with the most rolls counted in statistics."""
    pipeline = [
        {"$match": {"use_in_stats": True, "charid": {"$ne": None}}},
        {"$group": {"_id": "$charid", "rolls": {"$sum": 1}}},
        {"$sort": {"rolls": -1}},
        {"$limit": 1},
    ]
    results = list(db.rolls.aggregate(pipeline, allowDiskUse=True))
    if not results:
        raise SystemExit("No rolls found.")

    return results[0]["_id"], results[0]["rolls"]


def traits_pipeline(charid: ObjectId, date: datetime) -> Pipeline:
    """The Traits pipeline, run on the rolls collection."""
    return [
        {
            "$match": {
                "charid": charid,
                "use_in_stats": True,
                "date": {"$gte": date},
                "pool": {"$ne": None},
            }
        },
        {
            "$project": {
                "charid": 1,
                "pool": {"$split": ["$pool", " "]},
                "successes": {
                    "$add": [
                        {"$cond": [{"$ne": ["$reroll", None]}, "$reroll.margin", "$margin"]},
                        "$difficulty",
                    ]
                },
            }
        },
        {"$unwind": "$pool"},
        {
            "$group": {
                "_id": {"charid": "$charid", "pool": "$pool"},
                "count": {"$sum": "$successes"},
            }
        },
        {"$group": {"_id": "$_id.charid", "docs": {"$push": {"k": "$_id.pool", "v": "$count"}}}},
        {"$replaceRoot": {"newRoot": {"_id": "$_id", "traits": {"$arrayToObject": ["$docs"]}}}},
    ]


def general_pipeline(guild: int, user: int, date: datetime) -> Pipeline:
    """The General pipeline, run on the characters collection."""
    return [
        {"$match": {"guild": guild, "user": user}},
        {
            "$lookup": {
                "from": "rolls",
                "localField": "_id",
                "foreignField": "charid",
                "as": "rolls",
            }
        },
        {"$unwind": "$rolls"},
        {"$match": {"rolls.date": {"$gte": date}, "rolls.use_in_stats": True}},
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "rerolled": {"$cond": [{"$ne": ["$rolls.reroll", None]}, 1, 0]},
                "outcome": {
                    "$cond": [
                        {"$ne": ["$rolls.reroll", None]},
                        "$rolls.reroll.outcome",
                        "$rolls.outcome",
                    ]
                },
            }
        },
        {
            "$group": {
                "_id": {"charid": "$_id", "character": "$name", "outcome": "$outcome"},
                "outcome": {"$addToSet": "$outcome"},
                "rerolls": {"$sum": "$rerolled"},
                "count": {"$sum": 1},
            }
        },
        {
            "$group": {
                "_id": {"charid": "$_id.charid", "character": "$_id.character"},
                "rerolls": {"$sum": "$rerolls"},
                "outcomes": {"$push": {"k": {"$first": "$outcome"}, "v": "$count"}},
            }
        },
        {
            "$project": {
                "_id": "$_id.charid",
                "name": "$$ROOT._id.character",
                "rerolls": "$rerolls",
                "outcomes": {"$arrayToObject": "$outcomes"},
            }
        },
        {"$sort": {"name": 1}},
    ]


def timed(func: Callable[[], Any], runs: int) -> list[float]:
    """Time the function, returning each run's duration in seconds."""
    times = []
    for _ in range(runs):
        start = perf_counter()
        func()
        times.append(perf_counter() - start)
    return times


def report(name: str, times: list[float]):
    """Print the timings. The first run is the most likely to be uncached."""
    first, slowest = times[0], max(times)
    verdict = "OVER DEADLINE" if slowest >= DEADLINE else f"{slowest / DEADLINE:.0%} of deadline"
    print(
        f"{name:<8} first {first * 1000:8.1f} ms | "
        f"median {statistics.median(times) * 1000:8.1f} ms | "
        f"max {slowest * 1000:8.1f} ms | {verdict}"
    )


def main():
    parser = argparse.ArgumentParser(description="Benchmark the /statistics pipelines.")
    parser.add_argument("--prod", action="store_true", help="Use the production database")
    parser.add_argument("--runs", type=int, default=5, help="Runs per pipeline (default 5)")
    parser.add_argument("--date", default=DEFAULT_DATE, help="Start date, as YYYYMMDD")
    args = parser.parse_args()

    if args.prod:
        db = MongoClient(os.environ["INCONNU_MONGO"]).prod
    else:
        db = MongoClient(os.environ["INCONNU_DEV"]).dev
    date = datetime.strptime(args.date, "%Y%m%d")

    print(f"Database: {db.name}")
    print("Finding the character with the most rolls ...")
    charid, roll_count = find_top_character(db)
    char = db.characters.find_one({"_id": charid}, {"name": 1, "guild": 1, "user": 1})
    if char is None:
        raise SystemExit(f"Character {charid} has {roll_count} rolls, but no longer exists.")

    owner_chars = db.characters.count_documents({"guild": char["guild"], "user": char["user"]})
    print(f"Character: {char['name']} ({charid}), {roll_count} rolls")
    print(f"Owner has {owner_chars} character(s) on this server\n")

    report("Ping", timed(lambda: db.command("ping"), args.runs))

    traits = traits_pipeline(charid, date)
    report("Traits", timed(lambda: list(db.rolls.aggregate(traits)), args.runs))

    general = general_pipeline(char["guild"], char["user"], date)
    report("General", timed(lambda: list(db.characters.aggregate(general)), args.runs))


if __name__ == "__main__":
    main()
