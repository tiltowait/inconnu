"""experience/award_deduct.py - Award or deduct XP from a character."""

import discord

import inconnu

__HELP_URL = "https://www.inconnu-bot.com"


async def award_or_deduct(ctx, player, character, amount, scope, reason):
    """Award or deduct XP from a character."""
    try:
        owner = await inconnu.common.player_lookup(ctx, player)
        tip = "`/experience " + ("award" if amount > 0 else "deduct") + "`"
        character = await inconnu.common.fetch_character(
            ctx, character, tip, __HELP_URL, owner=owner
        )
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

        if await inconnu.settings.accessible(ctx.user):
            msg = { "content": __get_text(character, amount, scope, reason) }
        else:
            msg = { "embed": __get_embed(ctx, player, character, amount, scope, reason) }

        await ctx.respond(**msg)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


def __get_embed(ctx, player, character, amount, scope, reason):
    """Generate the embed."""
    title = "Awarded " if amount > 0 else "Deducted "
    title += f"{abs(amount)} {scope.title()} XP"

    embed = discord.Embed(title=title)
    embed.set_author(name=character.name, icon_url=player.display_avatar)
    embed.set_footer(text="To view: /experience log")

    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Staff", value=f"@{ctx.user.display_name}", inline=False)
    embed.add_field(
        name="New Experience (Unspent / Lifetime)",
        value=f"```{character.current_xp} / {character.total_xp}```",
        inline=False
    )

    return embed


def __get_text(character, amount, scope, reason):
    """Generate the plaintext message."""
    if amount > 0:
        verb = "Awarded"
        preposition = "to"
    else:
        verb = "Deducted"
        preposition = "from"

    msg = f"{verb} `{amount} {scope} experience` {preposition} **{character.name}**."
    msg += f"\n**Reason:** *{reason}*"
    msg += f"\n\n**New XP:** {character.current_xp} / {character.total_xp}"

    return msg
