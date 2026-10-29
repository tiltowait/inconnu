"""Mark guilds the bot left as inactive, so they're culled.

Before the fix, VGuild.leave() set `left` but never cleared `active`. Culling
requires `active: false`, so guilds the bot left were kept forever. A guild is
marked inactive if its last recorded event is a departure (`left` after
`joined`) and the bot isn't in it now. Join and leave events are missed while
the bot is down, so the bot's current guilds are fetched from Discord rather
than trusted to the database.

Dry run by default. Pass --apply to write. The bot token is read from a hidden
prompt, so it can't come from the wrong .env.
"""

import os
import sys
import time
from argparse import ArgumentParser
from datetime import UTC, datetime
from getpass import getpass

import httpx
from dotenv import load_dotenv
from pymongo import MongoClient

MONGO_ENV = "INCONNU_MONGO"  # Change if necessary
API = "https://discord.com/api/v10"
# Refuse to apply if the bot is in fewer guilds than this share of the guilds
# the database calls active, which means the token is probably another bot's
MIN_GUILD_SHARE = 0.5

load_dotenv()


def discord_client(token: str) -> httpx.Client:
    """A client for Discord's API, authorized as the bot."""
    headers = {
        "Authorization": f"Bot {token}",
        # Discord asks bots to identify themselves this way
        "User-Agent": "DiscordBot (https://github.com/tiltowait/inconnu, 1.0)",
    }
    return httpx.Client(base_url=API, headers=headers)


def bot_name(client: httpx.Client) -> str:
    """The name of the bot the token belongs to."""
    response = client.get("/users/@me")
    response.raise_for_status()
    return response.json()["username"]


def bot_guilds(client: httpx.Client) -> set[int]:
    """The IDs of every guild the bot is in."""
    guilds: set[int] = set()
    after = 0
    while True:
        response = client.get("/users/@me/guilds", params={"limit": 200, "after": after})
        if response.status_code == 429:
            if "json" not in response.headers.get("content-type", ""):
                # Cloudflare's temporary IP ban, not a route limit
                sys.exit(f"Blocked by Discord:\n{response.text[:500]}")
            wait = response.json()["retry_after"]
            print(f"Rate limited; retrying in {wait:.1f}s")
            time.sleep(wait)
            continue
        response.raise_for_status()

        # Pace requests to the route's limit rather than hitting it
        if response.headers.get("x-ratelimit-remaining") == "0":
            time.sleep(float(response.headers["x-ratelimit-reset-after"]))
        if not (page := response.json()):
            return guilds

        ids = [int(guild["id"]) for guild in page]
        guilds.update(ids)
        after = max(ids)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the changes")
    parser.add_argument(
        "--grace",
        action="store_true",
        help="Set `left` to now, giving each guild the full 30 days before it's culled",
    )
    args = parser.parse_args()

    if not (mongo_url := os.getenv(MONGO_ENV)):
        sys.exit(f"'{MONGO_ENV}' not set!")
    if not (token := getpass("Bot token: ").strip()):
        sys.exit("No token given!")

    print("Fetching guilds", end=" ... ", flush=True)

    with discord_client(token) as discord:
        name = bot_name(discord)
        current = bot_guilds(discord)

    print("done!")
    print(f"{name} is in {len(current)} guilds.")

    with MongoClient(mongo_url) as client:
        db = client.get_database()
        active = db.guilds.count_documents({"active": True})
        print(f"Database `{db.name}` has {active} active guilds.")
        too_few = len(current) < active * MIN_GUILD_SHARE

        candidates = db.guilds.find(
            {"active": True, "left": {"$ne": None}, "$expr": {"$gt": ["$left", "$joined"]}},
            {"guild": 1, "name": 1, "left": 1},
        )
        departed = [guild for guild in candidates if guild["guild"] not in current]

        for guild in departed:
            print(f"{guild['guild']}\t{guild['left']:%Y-%m-%d}\t{guild['name']}")
        print(f"\n{len(departed)} guilds to mark inactive.")

        if too_few:
            print(f"\nWARNING: {name} is in far fewer guilds than the database expects. Wrong bot?")
        if not args.apply:
            print("Dry run; pass --apply to write.")
            return
        if too_few:
            sys.exit("Refusing to apply.")

        update: dict = {"active": False}
        if args.grace:
            update["left"] = datetime.now(UTC)
        result = db.guilds.update_many(
            {"guild": {"$in": [guild["guild"] for guild in departed]}}, {"$set": update}
        )
        print(f"Marked {result.modified_count} guilds inactive.")


if __name__ == "__main__":
    main()
