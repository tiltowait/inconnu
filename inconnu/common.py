"""common.py - Commonly used functions."""

import discord


def pluralize(value: int, noun: str) -> str:
    """Pluralize a noun."""
    nouns = {"success": "successes"}

    pluralized = f"{value} {noun}"
    if value != 1:
        if noun in nouns:
            pluralized = f"{value} {nouns[noun]}"
        else:
            pluralized += "s"

    return pluralized


async def display_error(ctx, char_name, error):
    """Display an error in a nice embed."""
    embed = discord.Embed(
        title="Error",
        description=str(error),
        color=0xFF0000
    )
    embed.set_author(name=char_name, icon_url=ctx.author.avatar_url)

    if hasattr(ctx, "reply"):
        await ctx.reply(embed=embed)
    else:
        await ctx.respond(embed=embed, hidden=True)
