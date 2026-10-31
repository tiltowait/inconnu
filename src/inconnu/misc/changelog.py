"""Fetch and display changelog from GitHub."""

import re
from datetime import datetime
from typing import NamedTuple

import aiohttp
import discord
from discord.utils import format_dt

import ui
from config import settings
from ctx import AppCtx

CHANGELOG_URL = "https://github.com/tiltowait/inconnu/releases/latest"


class ReleaseInfo(NamedTuple):
    """Inconnu release data."""

    tag: str
    text: str
    published_at: datetime


def compact_text(text: str) -> str:
    """Remove extra newlines between headings."""
    text = text.replace("\r\n", "\n")
    compact = re.sub(r"^(#+ .*)\n{2,}", r"\1\n", text, flags=re.MULTILINE)
    tight = re.sub(r"\n{2,}(#+ )", r"\n\1", compact)

    return tight


def split_sections(text: str) -> list[str]:
    """Split changelog sections (delimited by "##") into separate parts."""
    compacted = compact_text(text)
    parts = re.split(r"\n(?=## )", compacted)
    return parts


def build_changelog(release: ReleaseInfo) -> discord.ui.DesignerView:
    """Build the changelog component."""
    sections = split_sections(release.text)
    view = discord.ui.DesignerView(
        discord.ui.TextDisplay(f"# Inconnu {release.tag}"),
        discord.ui.TextDisplay(f"-# Released {format_dt(release.published_at, 'D')}"),
        *(discord.ui.Container(discord.ui.TextDisplay(section)) for section in sections),
        discord.ui.Section(
            discord.ui.TextDisplay("​"),
            accessory=discord.ui.Button(
                label="All releases", url="https://github.com/tiltowait/inconnu/releases"
            ),
        ),
    )
    return view


async def show_changelog(ctx: AppCtx, hidden: bool):
    """Display Inconnu's changelog."""
    try:
        release = await fetch_changelog()
        paginator = discord.ext.commands.Paginator(prefix="", suffix="", max_size=4000)

        for line in changelog.split("\n"):
            paginator.add_line(line)

        embeds = []
        for page in paginator.pages:
            embed = discord.Embed(
                title=f"Inconnu {release.tag}", description=page, url=CHANGELOG_URL
            )
            embed.set_thumbnail(url=ctx.bot.me.display_avatar)
            embeds.append(embed)

        show_buttons = len(embeds) > 1
        paginator = discord.ext.pages.Paginator(
            embeds,
            author_check=False,
            show_disabled=show_buttons,
            show_indicator=show_buttons,
        )
        await paginator.respond(ctx.interaction, ephemeral=hidden)

    except aiohttp.ClientError, KeyError:
        await ui.embeds.error(ctx, "Unable to fetch changelog.")


async def fetch_changelog() -> ReleaseInfo:
    """Fetch the changelog from GitHub."""
    token = settings.github_token
    header = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    async with aiohttp.ClientSession(headers=header, raise_for_status=True) as session:
        async with session.get(
            "https://api.github.com/repos/tiltowait/inconnu/releases/latest"
        ) as res:
            json = await res.json()
            return ReleaseInfo(
                tag=json["tag_name"],
                text=json["body"],
                published_at=datetime.fromisoformat(json["published_at"]),
            )
