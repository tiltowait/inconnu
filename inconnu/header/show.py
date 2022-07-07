"""header/display.py - RP header display facilities."""

import discord

import inconnu

__HELP_URL = "https://www.inconnu.app/"


async def show_header(ctx: discord.ApplicationContext, character: str = None, **kwargs):
    """Display the character's header in an embed."""
    try:
        tip = "`/header` `options ...`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL)
        header = character.rp_header

        # Get any overrides
        header.blush = bool(kwargs["blush"] or header.blush)
        header.location = kwargs["location"] or header.location
        header.merits = kwargs["merits"] or header.merits
        header.flaws = kwargs["flaws"] or header.flaws
        header.temp = kwargs["temp"] or header.temp

        # Title should not have a trailing "•" if location is empty
        title = [character.name]
        if character.is_vampire:
            # Only vampires can blush
            title.append("Blushed" if header.blush else "Not Blushed")

        if header.location:
            title.append(header.location)

        # Merits, flaws, and trackers
        description_ = []
        if header.merits:
            description_.append(header.merits)
        if header.flaws:
            description_.append(header.flaws)
        if header.temp:
            description_.append(f"*{header.temp}*")

        # Tracker damage
        trackers = []
        if character.is_vampire:
            trackers.append(f"**Hunger** `{character.hunger}`")

        hp_damage = track_damage(character.superficial_hp, character.aggravated_hp)
        trackers.append(f"**HP** `{hp_damage}`")

        wp_damage = track_damage(character.superficial_wp, character.aggravated_wp)
        trackers.append(f"**WP** `{wp_damage}`")

        description_.append(" • ".join(trackers))

        embed = discord.Embed(title=" • ".join(title), description="\n".join(description_))
        embed.set_thumbnail(url=character.image_url)

        await ctx.respond(embed=embed)

    except ValueError as err:
        await inconnu.common.present_error(ctx, err, character=character.name, help_url=__HELP_URL)


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
