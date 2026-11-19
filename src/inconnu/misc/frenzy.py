"""misc/frenzy.py - Perform a frenzy check."""

from collections.abc import Iterable
from typing import NamedTuple

import discord

import errors
import inconnu
import services
from ctx import AppCtx
from models import FrenzyAdvantage, FrenzyPenalty, VChar
from services.haven import haven
from utils import get_avatar, get_message
from utils.text import pluralize
from utils.urls import docs_url, web_asset

__HELP_URL = docs_url("guides/gameplay-shortcuts#frenzy-checks")
FRENZY_FAIL_COLOR = 0x880000


class FrenzyOutcome(NamedTuple):
    """The outcome of a frenzy check."""

    passed: bool
    critical: bool
    pool: int
    dice: list[int]
    original: list[int] | None  # Before The Dream's re-roll
    notes: list[str]  # How the pool was modified


def _can_frenzy(character: VChar):
    """Raises an exception if the character can't frenzy."""
    if not character.is_vampire:
        raise errors.CharacterError("Only vampires can frenzy!")


@haven(__HELP_URL, _can_frenzy, "None of your characters are capable of frenzying.")
async def frenzy(
    ctx: AppCtx,
    character: VChar,
    difficulty: int,
    penalty: FrenzyPenalty | None,
    bonus: str | None,
):
    """Perform a frenzy check. The bonus is a number of dice or an
    advantage's value."""
    if bonus is None:
        dice, advantages = 0, []
    elif bonus.isdigit():
        dice, advantages = int(bonus), []
    else:
        dice, advantages = 0, [FrenzyAdvantage(bonus)]

    outcome = frenzy_roll(character, difficulty, penalty, dice, advantages)
    await character.save_changes()

    if outcome.passed:
        if outcome.critical:
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

    footer = [*outcome.notes, "Dice: " + ", ".join(map(str, outcome.dice))]
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
    await __generate_report_task(ctx, msg, character, outcome.passed)


def frenzy_roll(
    character: VChar,
    difficulty: int,
    penalty: FrenzyPenalty | None,
    bonus: int,
    advantages: Iterable[FrenzyAdvantage],
) -> FrenzyOutcome:
    """Make a frenzy check, logging its outcome on the character. Penalties
    leave at least one die; bonus dice and advantages add to that."""
    pool = character.frenzy_resist
    notes: list[str] = []

    if penalty is not None:
        reduced = max(pool - _penalty_dice(character, penalty), 1)
        if removed := pool - reduced:
            source = "the Brujah bane" if penalty == "brujah" else "the Malkavian compulsion"
            notes.append(f"-{pluralize(removed, 'die')} from {source}.")
        pool = reduced

    if bonus > 0:
        pool += bonus
        notes.append(f"{_bonus(bonus)}.")

    advantages = sorted(set(advantages))
    for advantage in advantages:
        if advantage.dice > 0:
            pool += advantage.dice
            notes.append(f"{_bonus(advantage.dice)} from {advantage.display}.")

    outcome = inconnu.Roll(pool, 0, difficulty)

    original = None
    if FrenzyAdvantage.THE_DREAM in advantages and outcome.can_reroll_failures:
        original = list(outcome.normal.dice)
        failures = min(outcome.normal.failures, 3)
        outcome.reroll("reroll_failures")
        dream = FrenzyAdvantage.THE_DREAM.display
        notes.append(f"Re-rolled {pluralize(failures, 'die')} from {dream}.")

    passed = outcome.total_successes >= difficulty
    if passed:
        character.log.frenzy_resisted += 1
    else:
        character.log.times_frenzied += 1

    return FrenzyOutcome(
        passed=passed,
        critical=passed and outcome.is_critical,
        pool=pool,
        dice=outcome.normal.dice,
        original=original,
        notes=notes,
    )


def _penalty_dice(character: VChar, penalty: FrenzyPenalty) -> int:
    """The dice a penalty removes, before the one-die floor."""
    return character.bane_severity if penalty == "brujah" else 2


def _bonus(count: int) -> str:
    """A count of bonus dice, e.g. "+2 bonus dice"."""
    return f"+{count} bonus {'die' if count == 1 else 'dice'}"


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
    await services.post_update(
        ctx=ctx,
        msg=msg,
        character=character,
        title=frenzy_update_title(passed),
        message=frenzy_update_message(character, passed),
        color=None if passed else FRENZY_FAIL_COLOR,
    )


def frenzy_update_title(passed: bool) -> str:
    """The update channel's title for a frenzy check."""
    return "Frenzy Success" if passed else "Frenzy Failure"


def frenzy_update_message(character: VChar, passed: bool) -> str:
    """The update channel's description of a frenzy check."""
    verbed = "passed" if passed else "failed"
    return f"**{character.name}** {verbed} a frenzy check."
