"""misc/bloodpotency.py - Look up Blood Potency ratings."""
# pylint: disable=line-too-long

import discord

import inconnu.common
import inconnu.settings


async def blood_potency(ctx, rating: int):
    """Display the Blood Potency rating."""
    potency = _RATINGS[rating]

    # Build the fields for text or embed display
    fields = []

    surge = "Add " + inconnu.common.pluralize(potency["surge"], "die")
    fields.append(("Blood Surge", surge))

    mend = inconnu.common.pluralize(potency["mend"], "pt")
    fields.append(("Damage Mended", f"{mend}. Superficial Damage"))

    if (bonus := potency["bonus"]) == 0:
        bonus = "None"
    else:
        bonus = f"+{bonus}"
    fields.append(("Power Bonus", bonus))

    reroll = potency["reroll"]
    match reroll:
        case 0:
            reroll = "None"
        case 1:
            reroll = "Level 1"
        case _:
            reroll = f"Level {reroll} and below"
    fields.append(("Discipline Re-Roll", reroll))

    fields.append(("Bane Severity", potency["severity"]))
    fields.append(("Feeding Penalty", potency["penalty"]))

    # Display it!

    if await inconnu.settings.accessible(ctx.user):
        await __display_text(ctx, rating, fields)
    else:
        await __display_embed(ctx, rating, fields)


async def __display_embed(ctx, rating, fields):
    """Display the Blood Potency in an embed."""
    embed = discord.Embed(title=f"Blood Potency {rating}")
    embed.set_footer(text="V5 Core p.216")

    for field, value in fields:
        embed.add_field(name=field, value=value, inline=True)

    await ctx.respond(embed=embed)


async def __display_text(ctx, rating, fields):
    """Display the Blood Potency in plain text."""
    message = f"**Blood Potency {rating}**\n\n"
    message += "\n".join(map(lambda f: f"**{f[0]}:** {f[1]}", fields))
    message += "\n\n*V5 Core p.216*"

    await ctx.respond(message)


_RATINGS = {
    0: {
        "surge": 1,
        "mend": 1,
        "bonus": 0,
        "reroll": 0,
        "severity": 0,
        "penalty": "None"
    },
    1: {
        "surge": 2,
        "mend": 1,
        "bonus": 0,
        "reroll": 1,
        "severity": 2,
        "penalty": "None"
    },
    2: {
        "surge": 2,
        "mend": 2,
        "bonus": 1,
        "reroll": 1,
        "severity": 2,
        "penalty": "Animal and bagged blood slake half Hunger"
    },
    3: {
        "surge": 3,
        "mend": 2,
        "bonus": 1,
        "reroll": 2,
        "severity": 3,
        "penalty": "Animal and bagged blood slake no Hunger"
    },
    4: {
        "surge": 3,
        "mend": 3,
        "bonus": 2,
        "reroll": 2,
        "severity": 3,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 1 less Hunger per human"
    },
    5: {
        "surge": 4,
        "mend": 3,
        "bonus": 2,
        "reroll": 3,
        "severity": 4,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 1 less Hunger per human\nMust drain and kill a human to reduce Hunger below 2"
    },
    6: {
        "surge": 4,
        "mend": 3,
        "bonus": 3,
        "reroll": 3,
        "severity": 4,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 2 less Hunger per human\nMust drain and kill a human to reduce Hunger below 2"
    },
    7: {
        "surge": 5,
        "mend": 3,
        "bonus": 3,
        "reroll": 4,
        "severity": 5,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 2 less Hunger per human\nMust drain and kill a human to reduce Hunger below 2"
    },
    8: {
        "surge": 5,
        "mend": 4,
        "bonus": 4,
        "reroll": 4,
        "severity": 5,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 2 less Hunger per human\nMust drain and kill a human to reduce Hunger below 3"
    },
    9: {
        "surge": 6,
        "mend": 4,
        "bonus": 4,
        "reroll": 5,
        "severity": 6,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 2 less Hunger per human\nMust drain and kill a human to reduce Hunger below 3"
    },
    10: {
        "surge": 6,
        "mend": 5,
        "bonus": 5,
        "reroll": 5,
        "severity": 6,
        "penalty": "Animal and bagged blood slake no Hunger\nSlake 3 less Hunger per human\nMust drain and kill a human to reduce Hunger below 3"
    }
}
