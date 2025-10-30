"""reference/statistics.py - View character roll statistics"""

from collections import defaultdict
from datetime import datetime, timedelta

import discord

import inconnu
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/command-reference/miscellaneous#statistics"
DT_ST = "D"


async def statistics(ctx, character, style: str, date: datetime, *, player: discord.Member | None):
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
        owner = await inconnu.common.player_lookup(ctx, player)

        # As Inconnu was originally made for Cape Town by Night, we will use
        # that server's weekly reset time as the cutoff--but only if we aren't
        # looking at the current date
        if date.date() != datetime.utcnow().date():
            date += timedelta(hours=19)

        if date > datetime.utcnow():
            # Can't get stats from the future
            date_fmt = discord.utils.format_dt(date, DT_ST)
            await ctx.respond(f"{date_fmt} is in the future!", ephemeral=True)
            return

        if style == "General":
            await __general_statistics(ctx, date, owner)
        else:
            await __traits_statistics(ctx, character, date, player=owner)

    except ValueError:
        await inconnu.embeds.error(ctx, f"`{date}` is not a valid date.")
    except LookupError as err:
        await inconnu.embeds.error(ctx, err, help_url=__HELP_URL)


@haven(__HELP_URL)
async def __traits_statistics(ctx, character, date, *, player):
    """View the statistics for all traits since a given date."""
    pipeline = [
        {
            "$match": {
                "charid": character.pk,
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
    raw_stats = await inconnu.db.rolls.aggregate(pipeline).to_list(length=1)

    if raw_stats:
        stats = {}

        for trait in character.traits:
            # The raw_stats object has a bunch of bogus data, such as
            # math operators and numbers, that we don't want. So we
            # get only those traits that the character actually has.
            # If there aren't any successes, we store a 0, because that
            # is useful information, too.
            stats[trait.name] = raw_stats[0]["traits"].get(trait.name, 0)

        await __display_trait_statistics(ctx, character, stats, date, player)
    else:
        if date.year < 2021:
            # Lifetime rolls
            await ctx.respond(f"**{character.name}** has never made any trait rolls.")
        else:
            # Rolls since a given date
            date_fmt = discord.utils.format_dt(date, DT_ST)
            await ctx.respond(f"**{character.name}** hasn't made any trait rolls since {date_fmt}.")


async def __display_trait_statistics(ctx, character, stats, date, owner):
    """Display the character traits in a paginated embed."""
    if date.year < 2021:
        title = f"{character.name}: Trait successes (Lifetime)"
    else:
        title = f"{character.name}: Trait successes since {discord.utils.format_dt(date, DT_ST)}"

    embed = discord.Embed(title=title)
    embed.set_author(name=owner.display_name, icon_url=inconnu.get_avatar(owner))

    for group, subgroups in inconnu.constants.GROUPED_TRAITS.items():
        embed.add_field(name="​", value=f"**{group}**", inline=False)
        for subgroup, traits in subgroups.items():
            trait_list = []
            for trait in traits:
                successes = stats.pop(trait, 0)
                trait_list.append(f"***{trait}***: `{successes}`")

            embed.add_field(name=subgroup, value="\n".join(trait_list), inline=True)

    # User-defined traits
    if stats:
        traits = [f"***{trait}:*** `{successes}`" for trait, successes in stats.items()]
        traits = "\n".join(traits)
        embed.add_field(name="​", value=f"**USER-DEFINED**\n{traits}", inline=False)

    footer = "The numbers represent the successes rolled for each trait during the time "
    footer += "period. All traits used in a roll are incremented equally by the number "
    footer += "of successes gained."
    embed.set_footer(text=footer)

    await ctx.respond(embed=embed)


async def __general_statistics(ctx, date, owner):
    """View the roll statistics for the user's characters."""
    col = inconnu.db.characters
    pipeline = [
        {
            "$match": {
                "guild": ctx.guild.id,
                "user": owner.id,
            }
        },
        {
            "$lookup": {
                "from": "rolls",
                "localField": "_id",
                "foreignField": "charid",
                "as": "rolls",
            }
        },
        {"$unwind": "$rolls"},
        {
            "$match": {
                "rolls.date": {"$gte": date},
                "rolls.use_in_stats": True,
            }
        },
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
    results = await col.aggregate(pipeline).to_list(length=None)

    if not results:
        if ctx.user == owner:
            await ctx.respond("You haven't made any rolls on any characters.", ephemeral=True)
        else:
            await ctx.respond(
                f"{owner.display_name} hasn't made any rolls on any characters.", ephemeral=True
            )
        return

    if await inconnu.settings.accessible(ctx):
        await __display_text(ctx, results, date)
    else:
        await __display_embed(ctx, results, date, owner)


async def __display_text(ctx, results, date):
    """Display the results using plain text."""
    if date.year < 2021:
        fmt_date = "(Lifetime)"
    else:
        fmt_date = "Since " + discord.utils.format_dt(date, DT_ST)

    msg = f"**Roll Statistics {fmt_date}**\n"
    for character in results:
        lines = [f"***{character['name']}***"]
        outcomes = defaultdict(int)
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


async def __display_embed(ctx, results, date, owner):
    """Display the statistics in an embed."""
    if date.year < 2021:
        fmt_date = "(Lifetime)"
    else:
        fmt_date = "Since " + discord.utils.format_dt(date, DT_ST)

    embed = discord.Embed(title=f"Roll Statistics {fmt_date}")
    embed.set_author(name=owner.display_name, icon_url=inconnu.get_avatar(owner))

    for character in results:
        outcomes = defaultdict(int)
        outcomes.update(character["outcomes"])

        lines = []
        lines.append(f"Criticals: `{outcomes['critical']}`")
        lines.append(f"Successes: `{outcomes['success']}`")
        lines.append(f"Messies: `{outcomes['messy']}`")
        lines.append(f"Failures: `{outcomes['fail']}`")
        lines.append(f"Total Failures: `{outcomes['total_fail']}`")
        lines.append(f"Bestial Failures: `{outcomes['bestial']}`")
        lines.append(f"Rerolls: `{character['rerolls']}`")

        embed.add_field(name=character["name"], value="\n".join(lines))

    await ctx.respond(embed=embed)
