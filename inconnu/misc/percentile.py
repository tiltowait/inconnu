"""misc/percentile.py - Roll a percentaile."""

import random

async def percentile(ctx, ceiling: int):
    """Roll between 1 and the ceiling."""
    if ceiling < 1:
        await ctx.respond("The ceiling must be greater than 0!", hidden=True)
        return

    result = random.randint(1, ceiling)
    await ctx.respond(f"Rolling 1-{ceiling}: **{result}**")
