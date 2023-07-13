"""Fetch and display changelog from GitHub."""

import os

import aiohttp
import discord
from aiocache import cached

import inconnu

CHANGELOG = "https://github.com/tiltowait/inconnu/releases/latest"


async def show_changelog(ctx: discord.ApplicationContext, hidden: bool):
    """Display Inconnu's changelog."""
    try:
        changelog = await fetch_changelog()

        # Embeds can take 4000 characters in the description field, but we keep
        # it at 2000 for the sake of not scrolling forever.
        paginator = discord.ext.commands.Paginator(prefix="", suffix="")

        for line in changelog.split("\n"):
            paginator.add_line(line)

        embeds = []
        for page in paginator.pages:
            embed = discord.Embed(title="Changelog", description=page, url=CHANGELOG)
            embed.set_thumbnail(url=ctx.bot.user.display_avatar)
            embeds.append(embed)

        show_buttons = len(embeds) > 1
        paginator = discord.ext.pages.Paginator(
            embeds,
            show_disabled=show_buttons,
            show_indicator=show_buttons,
        )
        await paginator.respond(ctx.interaction, ephemeral=hidden)

    except (aiohttp.ClientError, KeyError):
        await inconnu.utils.error(ctx, "Unable to fetch changelog.")


@cached()
async def fetch_changelog():
    """Fetch the changelog from GitHub."""
    token = os.getenv("GITHUB_TOKEN", "")
    header = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    async with aiohttp.ClientSession(headers=header, raise_for_status=True) as session:
        async with session.get(
            "https://api.github.com/repos/tiltowait/inconnu/releases/latest"
        ) as res:
            json = await res.json()
            return json["body"]
