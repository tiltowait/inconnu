"""header/display.py - RP header display facilities."""

import copy

import discord

import inconnu
from inconnu.models.rpheader import HeaderSubdoc
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/command-reference/characters/rp-headers"


@haven(__HELP_URL)
async def show_header(ctx: discord.ApplicationContext, character, **kwargs):
    """Display the character's header in an embed."""
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

    hp_damage = track_damage(header.health.superficial, header.health.aggravated)
    wp_damage = track_damage(header.willpower.superficial, header.willpower.aggravated)
    trackers.append(f"**HP** `{hp_damage}`")
    trackers.append(f"**WP** `{wp_damage}`")

    description_.append(" • ".join(trackers))

    embed = discord.Embed(
        # Ensure we don't exceed the title limit
        title=header.title,
        description="\n".join(description_),
        url=inconnu.profile_url(character.id),
    )
    embed.set_thumbnail(url=character.random_image_url())

    if header.temp:
        embed.set_footer(text=header.temp)

    return embed


def track_damage(sup: int, agg: int) -> str:
    """Generate a text value for the tracker damage."""
    # We want to keep the total HP/WP secret. Instead, just show damage
    damage = []
    if sup > 0:
        damage.append(f"-{sup}s")
    if agg > 0:
        damage.append(f"-{agg}a")

    if damage:
        return "/".join(damage)
    return "-0"
