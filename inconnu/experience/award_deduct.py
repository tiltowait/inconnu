"""experience/award_deduct.py - Award or deduct XP from a character."""

import discord

import inconnu

__HELP_URL = "https://www.inconnu.app"


async def award_or_deduct(ctx, player, character, amount, scope, reason):
    """Award or deduct XP from a character."""
    haven = inconnu.utils.Haven(
        ctx,
        owner=player,
        character=character,
        tip="`/experience " + ("award" if amount > 0 else "deduct") + "`",
        help=__HELP_URL,
    )
    character = await haven.fetch()
    scope = scope.lower()

    # Check that we aren't deducting more XP than they have
    if scope == "unspent" and character.current_xp + amount < 0:
        if character.current_xp == 0:
            errmsg = f"**{character.name}** has no XP!"
        else:
            errmsg = f"**{character.name}** only has `{character.current_xp}` xp to spend!"

        await inconnu.common.present_error(ctx, errmsg)
        return

    await character.apply_experience(amount, scope, reason, ctx.author.id)

    if reason[-1] != ".":
        reason += "."

    embed = __get_embed(ctx, player, character, amount, scope, reason)
    await ctx.respond(embed=embed, allowed_mentions=discord.AllowedMentions.none())


def __get_embed(ctx, player, character, amount, scope, reason):
    """Generate the embed."""
    title = "Awarded " if amount > 0 else "Deducted "
    title += f"{abs(amount)} {scope.title()} XP"

    embed = discord.Embed(title=title)
    embed.set_author(name=character.name, icon_url=inconnu.get_avatar(player))
    embed.set_footer(text="To view: /experience log")

    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Awarded By", value=ctx.user.mention, inline=False)
    embed.add_field(
        name="New Experience (Unspent / Lifetime)",
        value=f"```{character.current_xp} / {character.total_xp}```",
        inline=False,
    )

    return embed
