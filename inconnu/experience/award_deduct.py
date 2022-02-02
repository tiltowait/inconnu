"""experience/award_deduct.py - Award or deduct XP from a character."""

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

        # Generate the message
        if amount > 0:
            verb = "Awarded"
            preposition = "to"
        else:
            verb = "Deducted"
            preposition = "from"

        character.apply_experience(amount, scope == "unspent", reason, ctx.author.id)

        msg = f"{verb} `{amount} {scope} experience` {preposition} **{character.name}**."
        msg += f"\n**Reason:** *{reason}"

        if reason[-1] != ".":
            msg += "."
        msg += "*"

        # Add the new XP
        msg += f"\n\n**New XP:** {character.current_xp} / {character.total_xp}"

        await ctx.respond(msg)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass
