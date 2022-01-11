"""misc/frenzy.py - Perform a frenzy check."""
#pylint: disable=too-many-arguments

import discord

from .. import common
from ..roll import Roll
from ..settings import Settings

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=frenzy-checks"


async def frenzy(ctx, difficulty: int, penalty: str, character: str):
    """Perform a frenzy check."""
    try:
        tip = "`/frenzy` `character:CHARACTER`"
        character = await common.fetch_character(ctx, character, tip, __HELP_URL)
        frenzy_pool = character.frenzy_resist

        if penalty == "brujah":
            frenzy_pool = max(frenzy_pool - character.bane_severity, 1)
        elif penalty == "malkavian":
            frenzy_pool = max(frenzy_pool - 2, 1)

        outcome = Roll(frenzy_pool, 0, difficulty)

        if outcome.total_successes >= difficulty:
            if outcome.is_critical:
                title = "Critical Success!"
                message = "Resist frenzy without losing a turn."
                color = 0x00FF00
            else:
                title = "Success!"
                message = "You spend 1 turn resisting frenzy."
                color = 0x7777FF
        else:
            title = "Failure!"
            message = "You succumb to the Beast."
            color = 0x5C0700
            character.log("frenzy")

        footer = "Dice: " + ", ".join(map(str, outcome.normal.dice))
        if penalty == "brujah":
            footer = f"Subtracting {character.bane_severity} dice due to Brujah bane.\n{footer}"
        elif penalty == "malkavian":
            footer = f"Subtracting 2 dice due to Malkavian compulsion.\n{footer}"

        if Settings.accessible(ctx.author):
            await __display_text(ctx, title, message, character.name, difficulty, footer)
        else:
            await __display_embed(ctx, title, message, character.name, difficulty, footer, color)

    except common.FetchError:
        pass


async def __display_text(ctx, title: str, message: str, name: str, difficulty: str, footer: str):
    """Display the outcome in plain text."""
    await ctx.respond(f"**{name}: Frenzy {title} (diff. {difficulty})**\n{message}\n*{footer}*")


async def __display_embed(
    ctx, title: str, message: str, name: str, difficulty: str, footer: str, color: int
):
    """Display the frenzy outcome in an embed."""
    embed = discord.Embed(
        title=title,
        description=message,
        colour=color
    )
    author_field = f"{name}: Frenzy vs diff. {difficulty}"
    embed.set_author(name=author_field, icon_url=ctx.author.display_avatar)
    embed.set_footer(text=footer)

    if title == "Failure!":
        url = "https://www.inconnu-bot.com/images/assets/frenzy.webp"
        embed.set_thumbnail(url=url)

    await ctx.respond(embed=embed)
