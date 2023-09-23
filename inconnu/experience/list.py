"""experience/list.py - List XP expenditures/gains."""

from datetime import timezone

import discord
from discord.ext.commands import Paginator as Chunker
from discord.ext.pages import Paginator

import inconnu
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/advanced/administration/experience-management"


@haven(__HELP_URL)
async def list_events(ctx, character, ephemeral, *, player):
    """List a character's XP events."""
    embeds = await __get_embeds(ctx, character, player)
    paginator = Paginator(embeds, show_disabled=False)

    if isinstance(ctx, discord.ApplicationContext):
        await paginator.respond(ctx.interaction, ephemeral=ephemeral)
    else:
        await paginator.respond(ctx, ephemeral=ephemeral)


async def __get_embeds(ctx, character, player):
    """Make an embed in which to display the XP events."""
    chunks = await __get_chunks(ctx, character)

    embeds = []
    for page in chunks.pages:
        embed = discord.Embed(title="Experience Log", description=page)
        embed.set_author(name=character.name, icon_url=inconnu.get_avatar(player))
        embed.add_field(
            name="Experience (Unspent / Lifetime)",
            value=f"```{character.experience.unspent} / {character.experience.lifetime}```",
        )
        embeds.append(embed)

    return embeds


async def __get_chunks(ctx, character):
    """Get the event contents used by both embeds and text."""
    chunker = Chunker(prefix="", suffix="")

    for index, event in enumerate(reversed(character.experience.log)):
        # We need the date/time to be TZ-aware
        date = event["date"]
        date = date.replace(tzinfo=timezone.utc)
        date = discord.utils.format_dt(date, "d")

        exp = event["amount"]
        reason = event["reason"]
        scope = event["event"].split("_")[-1]

        # Construct the admin mention rather than fetching it
        admin = f"<@{event['admin']}>"

        text = f"{index + 1}. **{exp:+} {scope}: {reason}** - {admin} • {date}"

        chunker.add_line(text)

    if not chunker.pages:
        chunker.add_line("*No experience awards/deductions have been logged.*")

    return chunker
