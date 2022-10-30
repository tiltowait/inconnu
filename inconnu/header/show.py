"""header/display.py - RP header display facilities."""

import copy

import discord

import inconnu
from inconnu.models.rpheader import HeaderSubdoc

__HELP_URL = "https://docs.inconnu.app/command-reference/characters/rp-headers"


async def show_header(ctx: discord.ApplicationContext, character: str = None, **kwargs):
    """Display the character's header in an embed."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        tip="`/header` `options ...`",
        help=__HELP_URL,
    )
    character = await haven.fetch()
    header_doc = HeaderSubdoc.create(character, **kwargs)
    embed = header_embed(header_doc, character)

    resp = await ctx.respond(embed=embed)
    if isinstance(resp, discord.Interaction):
        message = await resp.original_response()
    else:
        message = resp

    await register_header(ctx, message, character)


async def register_header(ctx, message, character):
    """Register the header in the database."""
    await inconnu.db.headers.insert_one(
        {
            "character": {
                "guild": ctx.guild.id,
                "user": ctx.user.id,
                "charid": character.pk,
            },
            "channel": ctx.channel.id,
            "message": message.id,
            "timestamp": discord.utils.utcnow(),
        }
    )


def header_embed(header: inconnu.models.HeaderSubdoc, character: "VChar") -> discord.Embed:
    """Generate the header embed from the document."""
    # Title format: Name • Location (if applicable) • Blush (if applicable)
    # Location may be None if the user has never run /update header
    # Blush string may be None if the character isn't a vampire
    title = [character.name, header.blush_str]

    if header.location:
        title.append(header.location)

    # Merits, flaws, and trackers go in the description field
    description_ = []
    if header.merits:
        description_.append(header.merits)
    if header.flaws:
        description_.append(header.flaws)

    # Tracker damage
    trackers = []
    if header.hunger is not None:
        trackers.append(f"**Hunger** `{header.hunger}`")

    trackers.append(f"**HP** `{header.hp_damage}`")
    trackers.append(f"**WP** `{header.wp_damage}`")

    description_.append(" • ".join(trackers))

    embed = discord.Embed(
        # Ensure we don't exceed the title limit
        title=header.gen_title(character.name),
        description="\n".join(description_),
        url=inconnu.profile_url(character.id),
    )
    embed.set_thumbnail(url=character.random_image_url())

    if header.temp:
        embed.set_footer(text=header.temp)

    return embed
