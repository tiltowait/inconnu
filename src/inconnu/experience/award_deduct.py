"""experience/award_deduct.py - Award or deduct XP from a character."""

import discord

import services
import ui
from ctx import AppCtx
from models import VChar
from services.haven import haven
from utils import get_avatar
from utils.urls import docs_url

__HELP_URL = docs_url("advanced/storytellers/experience-management")


@haven(__HELP_URL)
async def award_or_deduct(
    ctx: AppCtx,
    character: VChar,
    amount: int,
    scope: str,
    reason: str,
    *,
    player: discord.Member,
):
    """Award or deduct XP from a character, if the server lets the user."""
    scope = scope.lower()

    if scope == "unspent":
        allowed = await services.settings.can_adjust_current_xp(ctx)
    else:
        allowed = await services.settings.can_adjust_lifetime_xp(ctx)
    if not allowed:
        err = f"This server doesn't let players adjust {scope} XP."
        await ui.embeds.error(ctx, err, help=__HELP_URL)
        return

    # Check that we aren't deducting more XP than they have
    experience = character.experience
    current = experience.unspent if scope == "unspent" else experience.lifetime
    if current + amount < 0:
        if current == 0:
            errmsg = f"**{character.name}** has no {scope} XP!"
        else:
            errmsg = f"**{character.name}** only has `{current}` {scope} XP!"

        await ui.embeds.error(ctx, errmsg)
        return

    character.apply_experience(amount, scope, reason, ctx.author.id)
    await character.save_changes()  # Before responding, so a failed response can't hide the change

    if reason[-1] not in ".!?":
        reason += "."

    embed = __get_embed(ctx, player, character, amount, scope, reason)
    await ctx.respond(embed=embed, allowed_mentions=discord.AllowedMentions.none())


def __get_embed(ctx, player, character, amount, scope, reason):
    """Generate the embed."""
    verb = "Awarded" if amount > 0 else "Deducted"
    title = f"{verb} {abs(amount)} {scope.title()} XP"

    embed = discord.Embed(title=title)
    embed.set_author(name=character.name, icon_url=get_avatar(player))
    embed.set_footer(text="To view: /experience log")

    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name=f"{verb} by", value=ctx.user.mention, inline=False)
    embed.add_field(
        name="New Experience (Unspent / Lifetime)",
        value=f"```{character.experience.unspent} / {character.experience.lifetime}```",
        inline=False,
    )

    return embed
