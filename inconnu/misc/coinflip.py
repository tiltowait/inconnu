"""misc/coin.py - Perform a simple coin flip."""

import random


async def coinflip(ctx):
    """Flip a coin."""
    roll = random.randint(1, 1001)
    if 1 <= roll <= 500:
        coin = "Heads"
    elif 501 <= roll <= 1000:
        coin = "Tails"
    else:
        coin = "Landed on the edge"

    await ctx.respond(f"**{coin}!**")
