"""misc/coin.py - Perform a simple coin flip."""

import random


async def coinflip(ctx):
    """Flip a coin."""
    coin = random.choice(["Heads", "Tails"])
    await ctx.respond(f"**{coin}!**")
