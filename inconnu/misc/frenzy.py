"""misc/frenzy.py - Perform a frenzy check."""
#pylint: disable=too-many-arguments

import asyncio
import discord

import inconnu

__HELP_URL = "https://www.inconnu-bot.com/#/additional-commands?id=frenzy-checks"


async def frenzy(ctx, difficulty: int, penalty: str, character: str):
    """Perform a frenzy check."""
    try:
        tip = "`/frenzy` `character:CHARACTER`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL)

        if not character.is_vampire:
            await ctx.respond("Only vampires need to roll frenzy!", ephemeral=True)
            return

        frenzy_pool = character.frenzy_resist

        if penalty == "brujah":
            frenzy_pool = max(frenzy_pool - character.bane_severity, 1)
        elif penalty == "malkavian":
            frenzy_pool = max(frenzy_pool - 2, 1)

        outcome = inconnu.Roll(frenzy_pool, 0, difficulty)

        if outcome.total_successes >= difficulty:
            if outcome.is_critical:
                title = "Critical Success!"
                message = "Resist frenzy without losing a turn."
                color = 0x00FF00
            else:
                title = "Success!"
                message = "You spend 1 turn resisting frenzy."
                color = 0x7777FF
        else:
            title = "Failure!"
            message = "You succumb to the Beast."
            color = 0x5C0700
            await character.log("frenzy")

        footer = "Dice: " + ", ".join(map(str, outcome.normal.dice))
        if penalty == "brujah":
            footer = f"Subtracting {character.bane_severity} dice due to Brujah bane.\n{footer}"
        elif penalty == "malkavian":
            footer = f"Subtracting 2 dice due to Malkavian compulsion.\n{footer}"

        # Display the message
        if await inconnu.settings.accessible(ctx.user):
            # Build the text version of the message
            name = character.name
            content = f"**{name}: Frenzy {title} (DC {difficulty})**\n{message}\n*{footer}*"
            msg_content = { "content": content }
        else:
            embed = __get_embed(ctx, title, message, character.name, difficulty, footer, color)
            msg_content = { "embed": embed }

        await asyncio.gather(
            __generate_report_task(ctx, character,outcome),
            inconnu.respond(ctx)(**msg_content)
        )

    except inconnu.common.FetchError:
        pass


def __get_embed(
    ctx, title: str, message: str, name: str, difficulty: str, footer: str, color: int
):
    """Display the frenzy outcome in an embed."""
    embed = discord.Embed(
        title=title,
        description=message,
        colour=color
    )
    author_field = f"{name}: Frenzy vs DC {difficulty}"
    embed.set_author(name=author_field, icon_url=ctx.user.display_avatar)
    embed.set_footer(text=footer)

    if title == "Failure!":
        url = "https://www.inconnu-bot.com/images/assets/frenzy.webp"
        embed.set_thumbnail(url=url)

    return embed


def __generate_report_task(ctx, character, outcome):
    """Generate a report for the update channel."""
    verbed = "passed" if outcome.is_successful else "failed"

    return inconnu.common.report_update(
        ctx=ctx,
        character=character,
        title="Frenzy Success" if outcome.is_successful else "Frenzy Failure",
        message=f"**{character.name}** {verbed} their frenzy check.",
        color=0x880000 if outcome.is_failure else discord.Embed.Empty
    )
