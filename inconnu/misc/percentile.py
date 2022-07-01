"""misc/percentile.py - Roll a percentaile."""

import inconnu


async def percentile(ctx, ceiling: int):
    """Roll between 1 and the ceiling."""
    if ceiling < 1:
        await ctx.respond("The ceiling must be greater than 0!", ephemeral=True)
        return

    result = inconnu.random(ceiling)
    await ctx.respond(f"Rolling 1-{ceiling}: **{result}**")
