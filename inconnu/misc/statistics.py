"""misc/statistics.py - View character roll statistics"""

import os
from collections import defaultdict

import discord
import pymongo

from ..settings import Settings

async def statistics(ctx):
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
