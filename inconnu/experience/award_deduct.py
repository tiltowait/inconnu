"""experience/award_deduct.py - Award or deduct XP from a character."""

import asyncio

import discord

import inconnu
from ctx import AppCtx
from inconnu.models import VChar
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/advanced/administration/experience-management"


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
    """Award or deduct XP from a character."""
    scope = scope.lower()

    # Check that we aren't deducting more XP than they have
    if scope == "unspent" and character.experience.unspent + amount < 0:
        if character.experience.unspent == 0:
            errmsg = f"**{character.name}** has no XP!"
        else:
            errmsg = f"**{character.name}** only has `{character.experience.unspent}` xp to spend!"

        await inconnu.common.present_error(ctx, errmsg)
        return

    character.apply_experience(amount, scope, reason, ctx.author.id)

    if reason[-1] != ".":
        reason += "."

    embed = __get_embed(ctx, player, character, amount, scope, reason)
    await asyncio.gather(
        ctx.respond(embed=embed, allowed_mentions=discord.AllowedMentions.none()),
        character.save(),
    )


def __get_embed(ctx, player, character, amount, scope, reason):
    """Generate the embed."""
    verb = "Awarded" if amount > 0 else "Deducted"
    title = f"{verb} {abs(amount)} {scope.title()} XP"

    embed = discord.Embed(title=title)
    embed.set_author(name=character.name, icon_url=inconnu.get_avatar(player))
    embed.set_footer(text="To view: /experience log")

    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name=f"{verb} by", value=ctx.user.mention, inline=False)
    embed.add_field(
        name="New Experience (Unspent / Lifetime)",
        value=f"```{character.experience.unspent} / {character.experience.lifetime}```",
        inline=False,
    )

    return embed
