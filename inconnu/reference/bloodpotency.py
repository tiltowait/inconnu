"""reference/bloodpotency.py - Look up Blood Potency ratings."""
# pylint: disable=line-too-long

import discord

import inconnu.common
import inconnu.settings


async def blood_potency(ctx, rating: int):
    """Display the Blood Potency rating."""
    potency = _RATINGS[rating]
    generations = potency["generations"]

    if generations == [4]:
        description = "Available only to the 4th Generation."
    else:
        description = "Available to Generations " + " through ".join(map(str, generations)) + "."

    embed = discord.Embed(title=f"Blood Potency {rating}", description=description)
    embed.set_footer(text="V5 Core p.216")

    # Add the fields
    surge = "Add " + inconnu.common.pluralize(potency["surge"], "die")
    embed.add_field(name="Blood Surge", value=surge)

    mend = inconnu.common.pluralize(potency["mend"], "pt")
    embed.add_field(name="Damage Mended", value=f"{mend}. Superficial Damage")

    if (bonus := potency["bonus"]) == 0:
        bonus = "None"
    else:
        bonus = f"+{bonus}"
    embed.add_field(name="Power Bonus", value=bonus)

    reroll = potency["reroll"]
    match reroll:
        case 0:
            reroll = "None"
        case 1:
            reroll = "Level 1"
        case _:
            reroll = f"Level {reroll} and below"
    embed.add_field(name="Discipline Re-Roll", value=reroll)

    embed.add_field(name="Bane Severity", value=potency["severity"])
    embed.add_field(name="Feeding Penalty", value=potency["penalty"])

    await ctx.respond(embed=embed)


_RATINGS = {
    0: {
        "surge": 1,
        "mend": 1,
        "bonus": 0,
        "reroll": 0,
        "severity": 0,
        "penalty": "None",
        "generations": [14, 16],
    },
    1: {
        "surge": 2,
        "mend": 1,
        "bonus": 0,
        "reroll": 1,
        "severity": 2,
        "penalty": "None",
        "generations": [10, 13],
    },
    2: {
        "surge": 2,
        "mend": 2,
        "bonus": 1,
        "reroll": 1,
        "severity": 2,
        "penalty": "Animal and bagged blood slake half Hunger",
        "generations": [8, 13],
    },
    3: {
        "surge": 3,
        "mend": 2,
        "bonus": 1,
        "reroll": 2,
        "severity": 3,
        "penalty": "Animal and bagged blood slake no Hunger",
        "generations": [6, 13],
    },
    4: {
        "surge": 3,
        "mend": 3,
        "bonus": 2,
        "reroll": 2,
        "severity": 3,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 1 less Hunger per human",
        "generations": [5, 11],
    },
    5: {
        "surge": 4,
        "mend": 3,
        "bonus": 2,
        "reroll": 3,
        "severity": 4,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 1 less Hunger per human\nMust drain and kill a human to reduce Hunger below 2",
        "generations": [4, 9],
    },
    6: {
        "surge": 4,
        "mend": 3,
        "bonus": 3,
        "reroll": 3,
        "severity": 4,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 2 less Hunger per human\nMust drain and kill a human to reduce Hunger below 2",
        "generations": [4, 8],
    },
    7: {
        "surge": 5,
        "mend": 3,
        "bonus": 3,
        "reroll": 4,
        "severity": 5,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 2 less Hunger per human\nMust drain and kill a human to reduce Hunger below 2",
        "generations": [4, 7],
    },
    8: {
        "surge": 5,
        "mend": 4,
        "bonus": 4,
        "reroll": 4,
        "severity": 5,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 2 less Hunger per human\nMust drain and kill a human to reduce Hunger below 3",
        "generations": [4, 6],
    },
    9: {
        "surge": 6,
        "mend": 4,
        "bonus": 4,
        "reroll": 5,
        "severity": 6,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 2 less Hunger per human\nMust drain and kill a human to reduce Hunger below 3",
        "genertations": [4, 5],
    },
    10: {
        "surge": 6,
        "mend": 5,
        "bonus": 5,
        "reroll": 5,
        "severity": 6,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 3 less Hunger per human\nMust drain and kill a human to reduce Hunger below 3",
        "generations": [4],
    },
}
