"""character/create/create.py - Handle new character creation."""

from datetime import UTC, datetime, timedelta

import discord
from discord.utils import format_dt

import services
import ui
from ctx import AppCtx
from errors import InconnuError
from utils import urls
from utils.permissions import is_admin


async def launch_wizard(ctx: AppCtx, spc: bool):
    """Launch a character creation wizard."""
    if ctx.guild is None:
        raise InconnuError("Unexpectedly got a null guild.")
    if spc and not is_admin(ctx):
        await ui.embeds.error(ctx, "You need Administrator permissions to make an SPC.")
        return

    token = services.wizard_cache.register(ctx.guild, ctx.user.id, spc)
    wizard_url = urls.wizard_url(token)

    expiration = datetime.now(UTC) + timedelta(seconds=services.wizard_cache.ttl)
    expiration = format_dt(expiration, "R")

    embed = discord.Embed(
        title="Click here to create your character",
        description=f"**Link expiration:** {expiration}.",
        url=wizard_url,
    )
    await ctx.respond(embed=embed, ephemeral=True)
