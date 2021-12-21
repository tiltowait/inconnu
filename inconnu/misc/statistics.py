"""misc/statistics.py - View character roll statistics"""

import os
import re
from collections import defaultdict
from datetime import datetime

import discord
import pymongo

from .. import common
from ..settings import Settings

EPOCH = "1970-01-01"


async def statistics(ctx, trait: str, date):
    """
    View the roll statistics for the user's characters.
    Args:
        trait (optional str): The trait to count
        date (optional date): The date from which to look

    If trait is not provided, the bot will simply tally all roll results
    across all characters for the given time period. If it's provided, however,
    the bot will count all successes and number of rolls for the indicated trait
    across all of the user's characters on the server.
    """
    try:
        date = datetime.strptime(date, "%Y%m%d")

        if trait is None:
            await __all_statistics(ctx, date)
        else:
            await __trait_statistics(ctx, trait.title(), date)

    except ValueError:
        await common.present_error(ctx, f"`{date}` is not a valid date.")


async def __trait_statistics(ctx, trait, date):
    """View the roll statistics for a given trait."""
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    rolls = client.inconnu.rolls
    pipeline = [
        {
            "$match": {
                "user": ctx.author.id,
                "guild": ctx.guild.id,
                "date": { "$gte": date },
                "pool": re.compile(trait, flags=re.I)
            }
        },
        {
            "$lookup": {
                "from": "characters",
                "localField": "charid",
                "foreignField": "_id",
                "as": "character"
            }
        },
        {
            "$unwind": "$character"
        },
        {
            "$project": {
                "name": "$character.name",
                "successes": {
                    "$add": [
                        {
                            "$cond": [
                                {
                                    "$ne": [
                                        "$reroll", None
                                    ]
                                },
                                "$reroll.margin",
                                "$margin"
                            ]
                        },
                        "$difficulty"
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": "$name",
                "num_rolls": { "$sum": 1 },
                "successes": { "$sum": "$successes" }
            }
        }
    ]
    stats = list(rolls.aggregate(pipeline))
    formatted_date = date.strftime("%Y-%m-%d")
    if len(stats) > 0:
        if Settings.accessible(ctx.author):
            await __trait_stats_text(ctx, trait, stats, formatted_date)
        else:
            await __trait_stats_embed(ctx, trait, stats, formatted_date)
    else:
        await ctx.respond(f"None of your characters have rolled `{trait}` since {date}.")


async def __trait_stats_embed(ctx, trait, stats, date):
    """Display the trait statistics in an embed."""
    if date == EPOCH:
        title = f"{trait}: Roll statistics (Lifetime)"
    else:
        title = f"{trait}: Roll statistics since {date}"
    embed = discord.Embed(title=title)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)

    for character in stats:
        name = character["_id"]
        rolls = character["num_rolls"]
        successes = character["successes"]

        field = f"Rolls: `{rolls}`\nSuccesses: `{successes}`"
        embed.add_field(name=name, value=field)

    embed.set_footer(text=f"If a character is missing, then no rolls were made with {trait}.")
    await ctx.respond(embed=embed)



async def __trait_stats_text(ctx, trait, stats, date):
    """Print the trait statistics in text."""
    if len(stats) > 0:
        if date == EPOCH:
            output = [f"**{trait}: Roll statistics (Lifetime)**"]
        else:
            output = [f"**{trait}: Roll statistics since {date}**\n"]

        for character in stats:
            name = character["_id"]
            rolls = character["num_rolls"]
            successes = character["successes"]

            output.append(f"**{name}**\nRolls: `{rolls}`\nSuccesses: `{successes}`\n")

        await ctx.respond("\n".join(output))
    else:
        await ctx.respond(f"None of your characters have rolled `{trait}` since {date}.")


async def __all_statistics(ctx, date):
    """View the roll statistics for the user's characters."""
    client = pymongo.MongoClient(os.environ["MONGO_URL"])
    col = client.inconnu.characters
    pipeline = [
        {
          "$match": {
            "guild": ctx.guild.id,
            "user": ctx.author.id
          }
        },
        {
          "$lookup": {
            "from": 'rolls',
            "localField": '_id',
            "foreignField": 'charid',
            "as": 'rolls'
          }
        },
        {
          "$unwind": '$rolls'
        },
        {
            "$match": {
                "rolls.date": { "$gte": date }
            }
        },
        {
          "$project": {
            "_id": 1,
            "name": 1,
            "rerolled": { "$cond": [ { "$ne": [ "$rolls.reroll", None ] }, 1, 0 ] },
            "outcome": {
                "$cond": [
                    { "$ne": [ '$rolls.reroll', None ] }, '$rolls.reroll.outcome', '$rolls.outcome'
                ]
            }
          }
        },
        {
          "$group": {
            "_id": { "charid": '$_id', "character": '$name', "outcome": '$outcome' },
            "outcome": { "$addToSet": '$outcome' },
            "rerolls": { "$sum": '$rerolled' },
            "count": { "$sum": 1 }
          }
        },
        {
          "$group": {
            "_id": { "charid": '$_id.charid', "character": '$_id.character' },
            "rerolls": { "$sum": "$rerolls" },
            "outcomes": { "$push": { "k": { "$first": '$outcome' }, "v": '$count' } }
          }
        },
        {
          "$project": {
            "_id": '$_id.charid',
            "name": '$$ROOT._id.character',
            "rerolls": '$rerolls',
            "outcomes": {
              "$arrayToObject": '$outcomes'
            }
          }
        },
        {
            "$sort": { "name": 1 }
        }
    ]
    results = list(col.aggregate(pipeline))
    client.close()

    if len(results) == 0:
        await ctx.respond("You haven't made any rolls on any characters.", hidden=True)
        return

    if Settings.accessible(ctx.author):
        await __display_text(ctx, results)
    else:
        await __display_embed(ctx, results)


async def __display_text(ctx, results):
    """Display the results using plain text."""
    msg = "**Roll Statistics**\n"
    for character in results:
        lines = [f"***{character['name']}***"]
        outcomes = defaultdict(lambda: 0)
        outcomes.update(character["outcomes"])

        lines.append(f"Criticals: `{outcomes['critical']}`")
        lines.append(f"Successes: `{outcomes['success']}`")
        lines.append(f"Messies: `{outcomes['messy']}`")
        lines.append(f"Failures: `{outcomes['fail']}`")
        lines.append(f"Total Failures: `{outcomes['total_fail']}`")
        lines.append(f"Bestial Failures: `{outcomes['bestial']}`")
        lines.append(f"Rerolls: `{character['rerolls']}`")

        msg += "\n" + "\n".join(lines)

    await ctx.respond(msg)


async def __display_embed(ctx, results):
    """Display the statistics in an embed."""
    embed = discord.Embed(title="Roll Statistics")
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)

    for character in results:
        outcomes = defaultdict(lambda: 0)
        outcomes.update(character["outcomes"])

        lines = []
        lines.append(f"Criticals: `{outcomes['critical']}`")
        lines.append(f"Successes: `{outcomes['success']}`")
        lines.append(f"Messies: `{outcomes['messy']}`")
        lines.append(f"Failures: `{outcomes['fail']}`")
        lines.append(f"Total Failures: `{outcomes['total_fail']}`")
        lines.append(f"Bestial Failures: `{outcomes['bestial']}`")
        lines.append(f"Rerolls: `{character['rerolls']}`")

        embed.add_field(name=character["name"], value="\n".join(lines), inline=False)

    await ctx.respond(embed=embed)
