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

        # Blush string
        blush = "Blushed" if header.blush else "Not Blushed"

        # Title should not have a trailing "•" if location is empty
        title = [character.name, blush]
        if header.location:
            title.append(header.location)

        # Tracker damage
        hp_damage = track_damage(character.superficial_hp, character.aggravated_hp)
        wp_damage = track_damage(character.superficial_wp, character.aggravated_wp)

        embed = discord.Embed(
            title=" • ".join(title),
            description=(
                f"{header.merits}\n"
                f"{header.flaws}\n"
                f"**Hunger** `{character.hunger}` • **HP:** `{hp_damage}` • **WP:** `{wp_damage}`\n"
            ),
        )
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
