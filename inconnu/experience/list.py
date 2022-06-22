"""experience/list.py - List XP expenditures/gains."""

from datetime import timezone

import discord
from discord.ext.commands import Paginator as Chunker
from discord.ext.pages import Paginator

import inconnu

__HELP_URL = "https://www.inconnu.app"


async def list_events(ctx, character, player, ephemeral):
    """List a character's XP events."""
    try:
        owner = await inconnu.common.player_lookup(ctx, player)
        tip = "`/experience list character:CHARACTER player:PLAYER`"
        character = await inconnu.common.fetch_character(
            ctx, character, tip, __HELP_URL, owner=owner
        )

        embeds = await __get_embeds(ctx, character, owner)
        paginator = Paginator(embeds, show_disabled=False)

        if isinstance(ctx, discord.ApplicationContext):
            await paginator.respond(ctx.interaction, ephemeral=ephemeral)
        else:
            await paginator.respond(ctx, ephemeral=ephemeral)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


async def __get_embeds(ctx, character, player):
    """Make an embed in which to display the XP events."""
    chunks = await __get_chunks(ctx, character)

    embeds = []
    for page in chunks.pages:
        embed = discord.Embed(title="Experience Log", description=page)
        embed.set_author(name=character.name, icon_url=inconnu.get_avatar(player))
        embed.add_field(
            name="Experience (Unspent / Lifetime)",
            value=f"```{character.current_xp} / {character.total_xp}```",
        )
        embeds.append(embed)

    return embeds


async def __get_chunks(ctx, character):
    """Get the event contents used by both embeds and text."""
    events = character.experience_log
    chunker = Chunker(prefix="", suffix="")

    for index, event in enumerate(reversed(events)):
        # We need the date/time to be TZ-aware
        date = event["date"]
        date = date.replace(tzinfo=timezone.utc)
        date = inconnu.gen_timestamp(date, "d")

        exp = event["amount"]
        reason = event["reason"]
        admin_id = event["admin"]
        scope = event["event"].split("_")[-1]

        # Get the admin discord.Member. Try the cache first.
        if (admin := ctx.guild.get_member(admin_id)) is None:
            admin = await ctx.guild.fetch_member(admin_id)

        text = f"*{index + 1}.* **{exp:+} {scope}: {reason}** - {admin.mention} • {date}"

        chunker.add_line(text)

    if not chunker.pages:
        chunker.add_line("*No experience awards/deductions have been logged.*")

    return chunker
