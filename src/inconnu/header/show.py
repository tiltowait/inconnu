"""header/display.py - RP header display facilities."""

import discord
from loguru import logger

import db
import errors
import inconnu
from ctx import AppCtx
from models import VChar
from models.rpheader import HeaderSubdoc
from services.haven import haven
from utils import get_avatar
from utils.permissions import is_supporter

__HELP_URL = "https://docs.inconnu.app/command-reference/characters/rp-headers"


@haven(__HELP_URL)
async def show_header(ctx: AppCtx, character: VChar, **kwargs):
    """Display the character's header in an embed."""
    header_doc = HeaderSubdoc.create(character, **kwargs)
    message = None
    try:
        if not is_supporter(ctx):
            raise errors.NotPremium
        if not ctx.bot.can_webhook(ctx.channel):
            raise errors.WebhookError

        await ctx.respond("Generating header ...", ephemeral=True, delete_after=1)

        webhook = await ctx.bot.prep_webhook(ctx.channel)
        webhook_avatar = character.profile_image_url or get_avatar(ctx.user)
        embed = header_embed(header_doc, character, True)

        message = await webhook.send(
            embed=embed, username=character.name, avatar_url=webhook_avatar, wait=True
        )
    except (errors.NotPremium, errors.WebhookError):
        embed = header_embed(header_doc, character, False)
        resp = await ctx.respond(embed=embed)
        if isinstance(resp, discord.WebhookMessage):
            # This extreme edge case has come up exactly once. It's possible
            # that webhook permissions were revoked mid-command (very unlikely
            # timing), or maybe Discord had a glitch. (Assuming there isn't a
            # bug in the code above.) Regardless, protect against the extremely
            # unlikely edge case.
            message = resp
        else:
            message = await resp.original_response()
    finally:
        if message is not None:
            await register_header(ctx, message, character)
        else:
            logger.warning(
                "Unable to register {}'s header ({}: {})",
                ctx.user.name,
                ctx.guild.name,
                ctx.guild.id,
            )


async def register_header(ctx, message, character):
    """Register the header in the database."""
    await db.headers.insert_one(
        {
            "character": {
                "guild": ctx.guild.id,
                "user": ctx.user.id,
                "charid": character.id,
                "spc": character.is_spc,
            },
            "channel": ctx.channel.id,
            "message": message.id,
            "timestamp": discord.utils.utcnow(),
        }
    )


def header_embed(header: HeaderSubdoc, character: VChar, webhook: bool) -> discord.Embed:
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

    embed = discord.Embed(description="\n".join(description_))
    embed.set_thumbnail(url=character.random_image_url())

    if webhook:
        embed.set_author(name=header.base_title, url=inconnu.profile_url(character.id_str))
    else:
        embed.title = header.title
        embed.url = inconnu.profile_url(character.id_str)

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
