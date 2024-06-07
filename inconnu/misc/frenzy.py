"""misc/frenzy.py - Perform a frenzy check."""
# pylint: disable=too-many-arguments

import discord

import inconnu
from config import web_asset
from inconnu.utils.haven import haven

__HELP_URL = "https://docs.inconnu.app/guides/gameplay-shortcuts#frenzy-checks"

__FRENZY_BONUSES = {
    "Jewel in the Garden": 4,
    "Cold Dead Hunger": 2,
    "Gentle Mind": 4,
    "The Heart of Darkness": 2,
}
__FRENZY_BONUSES.update({str(n): n for n in range(1, 8)})


def _can_frenzy(character):
    """Raises an exception if the character can't frenzy."""
    if not character.is_vampire:
        raise inconnu.errors.CharacterError("Only vampires can frenzy!")


@haven(__HELP_URL, _can_frenzy, "None of your characters are capable of frenzying.")
async def frenzy(ctx, character, difficulty: int, penalty: str, bonus: str):
    """Perform a frenzy check."""
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
        dice = "die" if bonus_dice == 1 else "dice"
        if bonus.isdigit():
            footer.append(f"{bonus_dice:+} bonus {dice}.")
        else:
            footer.append(f"{bonus_dice:+} bonus {dice} from {bonus}.")

    outcome = inconnu.Roll(frenzy_pool, 0, difficulty)

    if bonus == "The Dream":
        failures = min(outcome.normal.failures, 3)
        outcome.reroll("reroll_failures")

        dice = inconnu.common.pluralize(failures, "die")
        footer.append(f"Re-rolled {dice} from {bonus}")

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
        character.log("frenzy")

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

    inter = await ctx.respond(**msg_content)
    msg = await inconnu.get_message(inter)
    await __generate_report_task(ctx, msg, character, outcome)
    await character.commit()


def __get_embed(ctx, title: str, message: str, name: str, difficulty: str, footer: str, color: int):
    """Display the frenzy outcome in an embed."""
    embed = discord.Embed(title=title, description=message, colour=color)
    author_field = f"{name}: Frenzy vs DC {difficulty}"
    embed.set_author(name=author_field, icon_url=inconnu.get_avatar(ctx.user))
    embed.set_footer(text=footer)

    if title == "Failure!":
        embed.set_thumbnail(url=web_asset("frenzy.webp"))

    return embed


async def __generate_report_task(ctx, msg, character, outcome):
    """Generate a report for the update channel."""
    verbed = "passed" if outcome.is_successful else "failed"

    await inconnu.common.report_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title="Frenzy Success" if outcome.is_successful else "Frenzy Failure",
        message=f"**{character.name}** {verbed} a frenzy check.",
        color=0x880000 if outcome.is_failure else None,
    )
