"""Fetch and display changelog from GitHub."""

import re
from datetime import datetime
from typing import TYPE_CHECKING, NamedTuple

import aiohttp
from async_lru import alru_cache
from discord.ui import Button, Container, Section, TextDisplay
from discord.utils import format_dt

import ui
from config import settings
from ctx import AppCtx
from utils import re_paginate
from utils.cmdreplace import mention_commands

if TYPE_CHECKING:
    from bot import InconnuBot

RELEASES_URL = "https://github.com/tiltowait/inconnu/releases"
PAGE_SIZE = 3800  # Smaller than max limit of 4000 to allow for the title


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


def build_changelog(
    bot: InconnuBot, release: ReleaseInfo, note: str | None = None
) -> ui.views.PagedView:
    """Build the paginated changelog, one container per section. The optional
    note goes beside each page's releases link. `/command` text in either
    becomes a command mention."""
    # Mentions are longer than the text they replace, so substitute them
    # before paginating
    text = mention_commands(bot, compact_text(release.text)) or ""
    note = mention_commands(bot, note)

    pages = []
    for page in re_paginate([text], page_len=PAGE_SIZE):
        pages.append(
            [
                TextDisplay(f"# Inconnu {release.tag}"),
                TextDisplay(f"-# Released {format_dt(release.published_at, 'D')}"),
                *(Container(TextDisplay(section)) for section in split_sections(page)),
                Section(
                    TextDisplay(note or "\u200b"),  # Sections need text
                    accessory=Button(label="All releases", url=RELEASES_URL),
                ),
            ]
        )

    return ui.views.PagedView(pages)


async def show_changelog(ctx: AppCtx, hidden: bool):
    """Display Inconnu's changelog."""
    try:
        release = await fetch_changelog()
    except aiohttp.ClientError, KeyError:
        await ui.embeds.error(ctx, "Unable to fetch changelog.")
        return

    await ctx.respond(view=build_changelog(ctx.bot, release), ephemeral=hidden)


@alru_cache(ttl=3600)
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
