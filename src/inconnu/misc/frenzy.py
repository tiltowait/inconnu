"""misc/frenzy.py - Perform a frenzy check."""

import discord

import errors
import inconnu
import services
from ctx import AppCtx
from models import VChar
from services.haven import haven
from utils import get_avatar, get_message
from utils.text import pluralize
from utils.urls import docs_url, web_asset

__HELP_URL = docs_url("guides/gameplay-shortcuts#frenzy-checks")

__FRENZY_BONUSES = {
    "Jewel in the Garden": 4,
    "Cold Dead Hunger": 2,
    "Gentle Mind": 4,
    "The Heart of Darkness": 2,
}
__FRENZY_BONUSES.update({str(n): n for n in range(1, 8)})


def _can_frenzy(character: VChar):
    """Raises an exception if the character can't frenzy."""
    if not character.is_vampire:
        raise errors.CharacterError("Only vampires can frenzy!")


@haven(__HELP_URL, _can_frenzy, "None of your characters are capable of frenzying.")
async def frenzy(
    ctx: AppCtx, character: VChar, difficulty: int, penalty: str | None, bonus: str | None
):
    """Perform a frenzy check."""
    frenzy_pool = character.frenzy_resist
    footer: list[str] = []

    if penalty == "brujah":
        frenzy_pool = max(frenzy_pool - character.bane_severity, 1)
        footer.append(f"-{character.bane_severity} dice from the Brujah bane.")
    elif penalty == "malkavian":
        frenzy_pool = max(frenzy_pool - 2, 1)
        footer.append("-2 dice from the Malkavian compulsion.")

    if bonus is not None and (bonus_dice := __FRENZY_BONUSES.get(bonus)):
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

        dice = pluralize(failures, "die")
        footer.append(f"Re-rolled {dice} from {bonus}")

    passed = outcome.total_successes >= difficulty
    if passed:
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
    footer_text = "\n".join(footer)

    # Display the message
    if await services.settings.accessible(ctx):
        # Build the text version of the message
        name = character.name
        content = f"**{name}: Frenzy {title} (DC {difficulty})**\n{message}\n*{footer_text}*"
        inter = await ctx.respond(content)
    else:
        embed = __get_embed(ctx, title, message, character.name, difficulty, footer_text, color)
        inter = await ctx.respond(embed=embed)

    msg = await get_message(inter)
    await __generate_report_task(ctx, msg, character, passed)
    await character.save()


def __get_embed(
    ctx: AppCtx, title: str, message: str, name: str, difficulty: int, footer: str, color: int
) -> discord.Embed:
    """Display the frenzy outcome in an embed."""
    embed = discord.Embed(title=title, description=message, colour=color)
    author_field = f"{name}: Frenzy vs DC {difficulty}"
    embed.set_author(name=author_field, icon_url=get_avatar(ctx.user))
    embed.set_footer(text=footer)

    if title == "Failure!":
        embed.set_thumbnail(url=web_asset("frenzy.webp"))

    return embed


async def __generate_report_task(
    ctx: AppCtx, msg: discord.Message | None, character: VChar, passed: bool
):
    """Generate a report for the update channel."""
    verbed = "passed" if passed else "failed"

    await services.post_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title="Frenzy Success" if passed else "Frenzy Failure",
        message=f"**{character.name}** {verbed} a frenzy check.",
        color=None if passed else 0x880000,
    )
