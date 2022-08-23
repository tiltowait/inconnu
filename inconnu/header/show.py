"""header/display.py - RP header display facilities."""

import copy

import discord

import inconnu

__HELP_URL = "https://www.inconnu.app/"


async def show_header(ctx: discord.ApplicationContext, character: str = None, **kwargs):
    """Display the character's header in an embed."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        tip="`/header` `options ...`",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    # Prepare the header with any overrides
    header = copy.deepcopy(character.header)

    if kwargs["blush"] is not None:
        header.blush = kwargs["blush"]
    header.location = kwargs["location"] or header.location
    header.merits = kwargs["merits"] or header.merits
    header.flaws = kwargs["flaws"] or header.flaws
    header.temp = kwargs["temp"] or header.temp

    # Title should not have a trailing "•" if location is empty
    title = [character.name, inconnu.header.blush_text(character, header.blush)]

    if header.location:
        title.append(header.location)

    # Merits, flaws, and trackers
    description_ = []
    if header.merits:
        description_.append(header.merits)
    if header.flaws:
        description_.append(header.flaws)

    # Tracker damage
    trackers = []
    if character.is_vampire:
        trackers.append(f"**Hunger** `{character.hunger}`")

    hp_damage = track_damage(character.superficial_hp, character.aggravated_hp)
    trackers.append(f"**HP** `{hp_damage}`")

    wp_damage = track_damage(character.superficial_wp, character.aggravated_wp)
    trackers.append(f"**WP** `{wp_damage}`")

    description_.append(" • ".join(trackers))

    embed = discord.Embed(
        # Ensure we don't exceed the title limit
        title=inconnu.header.header_title(*title)[:256],
        description="\n".join(description_),
        url=inconnu.profile_url(character.id),
    )
    embed.set_thumbnail(url=character.random_image_url())

    if header.temp:
        embed.set_footer(text=header.temp)

    resp = await ctx.respond(embed=embed)
    if isinstance(resp, discord.Interaction):
        message = await resp.original_message()
    else:
        message = resp

    # Register the header in the database
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
