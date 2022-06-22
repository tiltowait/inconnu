"""misc/frenzy.py - Perform a frenzy check."""
# pylint: disable=too-many-arguments

import asyncio

import discord

import inconnu

__HELP_URL = "https://www.inconnu.app/#/additional-commands?id=frenzy-checks"

__FRENZY_BONUSES = {
    "The Dream": 3,
    "Jewel in the Garden": 4,
    "Cold Dead Hunger": 2,
    "Gentle Mind": 4,
}
__FRENZY_BONUSES.update({str(n): n for n in range(1, 6)})


async def frenzy(ctx, difficulty: int, penalty: str, bonus: str, character: str):
    """Perform a frenzy check."""
    try:
        tip = "`/frenzy` `character:CHARACTER`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL)

        if not character.is_vampire:
            await ctx.respond("Only vampires need to roll frenzy!", ephemeral=True)
            return

        frenzy_pool = character.frenzy_resist
        footer = []

        if penalty == "brujah":
            frenzy_pool = max(frenzy_pool - character.bane_severity, 1)
            footer.append(f"-{character.bane_severity} dice from the Brujah bane.")
        elif penalty == "malkavian":
            frenzy_pool = max(frenzy_pool - 2, 1)
            footer.append("-2 dice from the Malkavian compulsion.")

        if bonus_dice := __FRENZY_BONUSES.get(bonus):
            frenzy_pool += bonus_dice
            if bonus.isdigit():
                footer.append(f"{bonus_dice:+} bonus dice.")
            else:
                footer.append(f"{bonus_dice:+} bonus dice from {bonus}.")

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

        footer.append("Dice: " + ", ".join(map(str, outcome.normal.dice)))
        footer = "\n".join(footer)

        # Display the message
        if await inconnu.settings.accessible(ctx):
            # Build the text version of the message
            name = character.name
            content = f"**{name}: Frenzy {title} (DC {difficulty})**\n{message}\n*{footer}*"
            msg_content = {"content": content}
        else:
            embed = __get_embed(ctx, title, message, character.name, difficulty, footer, color)
            msg_content = {"embed": embed}

        inter = await inconnu.respond(ctx)(**msg_content)
        msg = await inconnu.get_message(inter)
        await __generate_report_task(ctx, msg, character, outcome)

    except inconnu.common.FetchError:
        pass


def __get_embed(ctx, title: str, message: str, name: str, difficulty: str, footer: str, color: int):
    """Display the frenzy outcome in an embed."""
    embed = discord.Embed(title=title, description=message, colour=color)
    author_field = f"{name}: Frenzy vs DC {difficulty}"
    embed.set_author(name=author_field, icon_url=inconnu.get_avatar(ctx.user))
    embed.set_footer(text=footer)

    if title == "Failure!":
        url = "https://www.inconnu.app/images/assets/frenzy.webp"
        embed.set_thumbnail(url=url)

    return embed


async def __generate_report_task(ctx, msg, character, outcome):
    """Generate a report for the update channel."""
    verbed = "passed" if outcome.is_successful else "failed"

    await inconnu.common.report_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title="Frenzy Success" if outcome.is_successful else "Frenzy Failure",
        message=f"**{character.name}** {verbed} their frenzy check.",
        color=0x880000 if outcome.is_failure else discord.Embed.Empty,
    )
