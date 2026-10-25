"""Tests for inconnu/vr/rolldisplay.py embed, button generation, and button presses."""

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from typing import Any, cast
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import discord
import pytest
from beanie import PydanticObjectId
from discord.ui import Button

import inconnu
from ctx import AppCtx
from inconnu.character.impairment import impairment_reminder
from inconnu.vr.rolldisplay import RollDisplay
from models import Impairment, VChar
from tests.characters import gen_char

AVATAR = "https://example.com/avatar.png"
GUILD_ICON = "https://example.com/guild.png"
MESSAGE_ID = 4

type PressHelper = Callable[["Screen"], Awaitable[None]]


@pytest.fixture
def owner() -> discord.Member:
    """The player who made the roll."""
    member = MagicMock(spec=discord.Member)
    member.id = 1
    member.display_name = "tiltowait"
    member.guild_avatar = AVATAR
    return member


@pytest.fixture
def intruder() -> discord.Member:
    """A player who didn't make the roll."""
    member = MagicMock(spec=discord.Member)
    member.id = 5
    return member


@pytest.fixture
def ctx() -> AppCtx:
    """A mock AppCtx in a guild with an icon."""
    ctx = MagicMock(spec=AppCtx)
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 2
    ctx.guild.icon = GUILD_ICON
    ctx.channel = MagicMock(spec=discord.TextChannel)
    ctx.channel.id = 3
    ctx.respond = AsyncMock()  # A property on ApplicationContext, so the spec can't infer it
    return ctx


@pytest.fixture(autouse=True)
def mock_can_emoji() -> Iterator[AsyncMock]:
    """Allow emoji by default."""
    with patch("services.settings.can_emoji", new_callable=AsyncMock, return_value=True) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_emojis() -> Iterator[None]:
    """Replace dice emoji with readable placeholders."""
    names = [
        f"{kind}_{face}" for kind in ("ln", "h") for face in ("bestial", "crit", "succ", "fail")
    ]
    with patch("services.emojis", {name: f":{name}:" for name in names}):
        yield


@pytest.fixture(autouse=True)
def mock_log_roll() -> Iterator[AsyncMock]:
    """Prevent roll logging."""
    with patch("inconnu.stats.log_roll", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_get_message() -> Iterator[AsyncMock]:
    """Give the first response a message ID."""
    message = MagicMock(spec=discord.Message)
    message.id = MESSAGE_ID
    with patch("inconnu.vr.rolldisplay.get_message", new_callable=AsyncMock) as mock:
        mock.return_value = message
        yield mock


@pytest.fixture(autouse=True)
def mock_rouse() -> Iterator[AsyncMock]:
    """Prevent surge Rouse checks."""
    with patch("inconnu.misc.rouse", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_char_display() -> Iterator[AsyncMock]:
    """Prevent the Willpower Spent display."""
    with patch("inconnu.character.display", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_char_save() -> Iterator[AsyncMock]:
    """Prevent character saves."""
    with patch("models.vchar.VChar.save", new_callable=AsyncMock) as mock:
        yield mock


def make_char(splat: str, hunger=1) -> VChar:
    """Generate a PC with an ID and the given Hunger."""
    char = gen_char(splat)
    char.id = PydanticObjectId()
    char.user = 1  # gen_char's user matches SPC_OWNER
    char.name = "Nadea Theron"
    char.hunger = hunger
    return char


def make_roll(
    normal: list[int],
    hunger: list[int],
    difficulty=0,
    pool_str: str | None = None,
    hunger_rating: int | None = None,
    impairment_penalty=Impairment.NONE,
) -> inconnu.Roll:
    """Generate a roll with predetermined dice."""
    if hunger_rating is None:
        hunger_rating = len(hunger)
    roll = inconnu.Roll(
        len(normal) + len(hunger),
        hunger_rating,
        difficulty,
        pool_str=pool_str,
        impairment_penalty=impairment_penalty,
    )
    roll.normal.dice = normal
    roll.hunger.dice = hunger
    return roll


def make_display(
    ctx: AppCtx,
    owner: discord.Member,
    roll: inconnu.Roll,
    comment: str | None = None,
    character: VChar | None = None,
    listener: AsyncMock | None = None,
    timeout: AsyncMock | None = None,
    ignore_impairment=False,
) -> RollDisplay:
    """Create a RollDisplay, optionally with a listener and timeout handler."""
    return RollDisplay(
        ctx,
        roll,
        comment,
        character,
        owner,
        listener,
        timeout,
        ignore_impairment=ignore_impairment,
    )


def field_map(embed: discord.Embed) -> dict[str, str]:
    """Map the embed's field names to values."""
    return {field.name: field.value for field in embed.fields}


def button_summary(buttons: list | None) -> list[tuple] | None:
    """Reduce buttons to (label, style, disabled, row)."""
    if buttons is None:
        return None
    return [(b.label, b.style, b.disabled, b.row) for b in buttons]


# Title, color, thumbnail


@pytest.mark.parametrize(
    "normal,hunger,difficulty,title,color,thumbnail",
    [
        ([6, 6, 2], [], 2, "SUCCESS! (2)", 0x7777FF, "success"),
        ([6, 2], [], 2, "FAILURE! (1)", 0x808080, "fail"),
        ([2, 3], [], 1, "TOTAL FAILURE!", 0x000000, "total-fail"),
        ([6], [1], 2, "BESTIAL FAILURE!", 0x5C0700, "bestial"),
        ([10, 10], [], 3, "CRITICAL! (4)", 0x00FF00, "crit"),
        ([10], [10], 1, "MESSY CRITICAL! (4)", 0xEA3323, "messy"),
    ],
)
async def test_embed_outcome_presentation(
    ctx: AppCtx,
    owner: discord.Member,
    normal: list[int],
    hunger: list[int],
    difficulty: int,
    title: str,
    color: int,
    thumbnail: str,
):
    """Each outcome has its own title, color, and thumbnail."""
    display = make_display(ctx, owner, make_roll(normal, hunger, difficulty))
    embed = await render(display)
    assert embed.thumbnail is not None

    assert embed.title == title
    assert embed.colour == discord.Colour(color)
    assert embed.thumbnail.url == f"https://assets.inconnu.app/dice/{thumbnail}.webp"


async def test_embed_after_reroll(ctx: AppCtx, owner: discord.Member):
    """Rerolls prefix the title, add the strategy, and show the original outcome."""
    roll = make_roll([6, 2], [], 2)
    display = make_display(ctx, owner, roll)

    screen = await show(display)
    with patch("inconnu.d10", return_value=10):
        await press_reroll_failures(screen)
    embed = screen.embed
    assert embed is not None and embed.author is not None

    assert embed.title == "R: SUCCESS! (2)"
    assert embed.author.name == "tiltowait • DC 2 • Rerolling Failures"

    last = embed.fields[-1]
    assert last.name == "Original Outcome"
    assert last.value == "```Failure (1)```"
    assert not last.inline


# Author line


async def test_author_without_character(ctx: AppCtx, owner: discord.Member):
    """Without a character, the author is the player, and DC 0 is omitted."""
    display = make_display(ctx, owner, make_roll([6], [], 0))
    embed = await render(display)
    assert embed.author is not None

    assert embed.author.name == "tiltowait"
    assert embed.author.icon_url == AVATAR


async def test_author_with_character(ctx: AppCtx, owner: discord.Member):
    """A PC's name is shown with the player's avatar."""
    display = make_display(ctx, owner, make_roll([6], [], 3), character=make_char("vampire"))
    embed = await render(display)
    assert embed.author is not None

    assert embed.author.name == "Nadea Theron • DC 3"
    assert embed.author.icon_url == AVATAR


async def test_author_with_spc(ctx: AppCtx, owner: discord.Member):
    """An SPC gets the SPC marker and the guild icon."""
    char = make_char("vampire")
    char.user = VChar.SPC_OWNER
    display = make_display(ctx, owner, make_roll([6], [], 0), character=char)
    embed = await render(display)
    assert embed.author is not None

    assert embed.author.name == "Nadea Theron (SPC)"
    assert embed.author.icon_url == GUILD_ICON


# Dice field


async def test_dice_field_emoji(ctx: AppCtx, owner: discord.Member):
    """Dice are shown as emoji in rolled order, normal then hunger."""
    display = make_display(ctx, owner, make_roll([2, 10, 6], [1, 7], 3))
    embed = await render(display)
    field = embed.fields[0]

    assert field.name == "Margin: 0"
    assert field.value == ":ln_fail: :ln_crit: :ln_succ: :h_bestial: :h_succ:"
    assert not field.inline


async def test_dice_field_emoji_max_pool(ctx: AppCtx, owner: discord.Member):
    """A pool of exactly 30 still uses emoji."""
    display = make_display(ctx, owner, make_roll([6] * 30, []))
    embed = await render(display)

    assert ":ln_succ:" in embed.fields[0].value


async def test_dice_field_text_when_emoji_disallowed(
    ctx: AppCtx, owner: discord.Member, mock_can_emoji: AsyncMock
):
    """Accessibility mode shows sorted dice as text."""
    mock_can_emoji.return_value = False
    display = make_display(ctx, owner, make_roll([2, 10, 6], [1, 7], 3))
    embed = await render(display)
    field = embed.fields[0]

    assert field.name == "Margin: 0"
    assert field.value == "**Normal Dice:** 10, 6, 2\n**Hunger Dice:** 7, 1"
    assert not field.inline


async def test_dice_field_text_when_pool_too_large(ctx: AppCtx, owner: discord.Member):
    """Pools over 30 dice fall back to text."""
    display = make_display(ctx, owner, make_roll([6] * 31, []))
    embed = await render(display)

    assert (
        embed.fields[0].value == "**Normal Dice:** " + ", ".join(["6"] * 31) + "\n**Hunger:** None"
    )


async def test_dice_field_text_hunger_only(
    ctx: AppCtx, owner: discord.Member, mock_can_emoji: AsyncMock
):
    """With no normal dice, only the Hunger line is shown."""
    mock_can_emoji.return_value = False
    display = make_display(ctx, owner, make_roll([], [3, 8]))
    embed = await render(display)

    assert embed.fields[0].value == "**Hunger Dice:** 8, 3"


# Stat fields


async def test_stat_fields(ctx: AppCtx, owner: discord.Member):
    """Dice, Hunger, and Difficulty are inline fields in order."""
    display = make_display(ctx, owner, make_roll([6, 6, 6], [2, 2], 4))
    embed = await render(display)

    stats = [(f.name, f.value, f.inline) for f in embed.fields[1:4]]
    assert stats == [("Dice", "5", True), ("Hunger", "2", True), ("Difficulty", "4", True)]
    assert len(embed.fields) == 4  # No pool, not rerolled


@pytest.mark.parametrize(
    "pool_str,expected",
    [
        ("Strength + Brawl", "Strength + Brawl"),
        ("strength + brawl", "Strength + Brawl"),
        ("Dexterity + AnimalKen", "Dexterity + Animal Ken"),
        ("Wits + blood_potency", "Wits + Blood Potency"),
        ("Wits + XYZ", "Wits + XYZ"),
    ],
)
async def test_pool_field(ctx: AppCtx, owner: discord.Member, pool_str: str, expected: str):
    """Pool strings are de-cameled and capitalized without lowercasing."""
    display = make_display(ctx, owner, make_roll([6], [], pool_str=pool_str))
    embed = await render(display)
    field = embed.fields[4]

    assert field.name == "Pool"
    assert field.value == expected
    assert field.inline


@pytest.mark.parametrize(
    "penalty,expected",
    [
        (Impairment.PHYSICAL, "Strength + Brawl -2 (physical impairment)"),
        (Impairment.MENTAL, "Strength + Brawl -2 (mental impairment)"),
        (Impairment.TOTAL, "Strength + Brawl -2 (total impairment)"),
    ],
)
async def test_pool_field_with_impairment_penalty(
    ctx: AppCtx, owner: discord.Member, penalty: Impairment, expected: str
):
    """An applied penalty is shown in the Pool field, in lowercase."""
    roll = make_roll([6], [], pool_str="Strength + Brawl", impairment_penalty=penalty)
    embed = await render(make_display(ctx, owner, roll, character=make_char("vampire")))

    assert field_map(embed)["Pool"] == expected


# Hunger field


@pytest.mark.parametrize(
    "splat,char_hunger,hunger_dice,expected",
    [
        (None, 0, [5, 5], "2"),
        (None, 0, [], "0"),
        ("vampire", 0, [], "*Sated*"),
        ("vampire", 2, [5, 5], "2 (Current)"),
        ("vampire", 3, [5], "1"),
        ("vampire", 2, [], "0"),
        ("thin-blood", 0, [], "*Sated*"),
        ("thin-blood", 1, [5], "1 (Current)"),
        ("mortal", 0, [], "*Mortal*"),
        ("ghoul", 0, [], "*Mortal*"),
    ],
)
async def test_hunger_field(
    ctx: AppCtx,
    owner: discord.Member,
    splat: str | None,
    char_hunger: int,
    hunger_dice: list[int],
    expected: str,
):
    """The Hunger field reflects the character's Hunger and splat."""
    char = make_char(splat, char_hunger) if splat is not None else None
    display = make_display(ctx, owner, make_roll([6], hunger_dice), character=char)
    embed = await render(display)

    assert field_map(embed)["Hunger"] == expected


async def test_hunger_field_sated_requires_no_hunger_dice(ctx: AppCtx, owner: discord.Member):
    """A Hunger 0 vampire who rolls Hunger dice anyway sees the rating."""
    display = make_display(
        ctx, owner, make_roll([6], [5], hunger_rating=1), character=make_char("vampire", 0)
    )
    embed = await render(display)

    assert field_map(embed)["Hunger"] == "1"


# Footer


async def test_footer_absent(ctx: AppCtx, owner: discord.Member):
    """No comment and no impairment means no footer."""
    display = make_display(ctx, owner, make_roll([6], []), character=make_char("vampire"))
    embed = await render(display)

    assert embed.footer is None


async def test_footer_comment(ctx: AppCtx, owner: discord.Member):
    """The comment is the footer."""
    display = make_display(ctx, owner, make_roll([6], []), comment="Hello")
    embed = await render(display)
    assert embed.footer is not None

    assert embed.footer.text == "Hello"


async def test_footer_impairment_only(ctx: AppCtx, owner: discord.Member):
    """Impairment is shown even without a comment."""
    char = make_char("vampire")
    char.willpower = "xxxxx"
    display = make_display(ctx, owner, make_roll([6], []), character=char)
    embed = await render(display)
    assert embed.footer is not None

    assert embed.footer.text == impairment_reminder(char)


async def test_footer_comment_and_impairment(ctx: AppCtx, owner: discord.Member):
    """Impairment is appended to the comment on a new line."""
    char = make_char("vampire")
    char.willpower = "xxxxx"
    display = make_display(ctx, owner, make_roll([6], []), comment="Hello", character=char)
    embed = await render(display)
    assert embed.footer is not None

    assert embed.footer.text == f"Hello\n{impairment_reminder(char)}"


# Impairment notes

PHYSICALLY_IMPAIRED = "//////"


async def test_footer_penalty_applied(ctx: AppCtx, owner: discord.Member):
    """An applied penalty replaces the reminder; the Pool field shows it instead."""
    char = make_char("vampire")
    char.health = PHYSICALLY_IMPAIRED
    roll = make_roll([6], [], pool_str="Strength + Brawl", impairment_penalty=Impairment.PHYSICAL)
    embed = await render(make_display(ctx, owner, roll, comment="Hello", character=char))
    assert embed.footer is not None

    assert embed.footer.text == "Hello"


@pytest.mark.parametrize("comment,expected", [(None, ""), ("Hello", "Hello\n")])
async def test_footer_penalty_ignored(
    ctx: AppCtx, owner: discord.Member, comment: str | None, expected: str
):
    """Ignoring a penalty that would apply shows an override notice."""
    char = make_char("vampire")
    char.health = PHYSICALLY_IMPAIRED
    roll = make_roll([6], [], pool_str="Strength + Brawl")
    display = make_display(ctx, owner, roll, comment, char, ignore_impairment=True)
    embed = await render(display)
    assert embed.footer is not None

    assert embed.footer.text == expected + "Override: Impairment ignored"


async def test_footer_ignored_penalty_that_would_not_apply(ctx: AppCtx, owner: discord.Member):
    """Ignoring has no effect on rolls the impairment doesn't penalize, so the
    reminder is shown instead of an override notice."""
    char = make_char("vampire")
    char.health = PHYSICALLY_IMPAIRED
    roll = make_roll([6], [], pool_str="Wits + Awareness")
    embed = await render(make_display(ctx, owner, roll, character=char, ignore_impairment=True))
    assert embed.footer is not None

    assert embed.footer.text == impairment_reminder(char)


@pytest.mark.parametrize(
    "penalty,ignore",
    [(Impairment.PHYSICAL, False), (Impairment.NONE, True), (Impairment.NONE, False)],
)
async def test_footer_incapacitation_takes_priority(
    ctx: AppCtx, owner: discord.Member, penalty: Impairment, ignore: bool
):
    """Torpor and death are always shown, whatever happened to the penalty."""
    char = make_char("vampire")
    char.health = "xxxxxx"
    roll = make_roll([6], [], pool_str="Strength + Brawl", impairment_penalty=penalty)
    display = make_display(ctx, owner, roll, "Hello", char, ignore_impairment=ignore)
    embed = await render(display)
    assert embed.footer is not None

    assert embed.footer.text == "Hello\nYou are IN TORPOR!"


# Surging


@pytest.mark.parametrize(
    "pool_str,comment,expected",
    [
        (None, "surge", True),
        (None, "Surge", True),
        (None, "SURGE for the win", True),
        (None, "biting, surge", True),
        ("Strength + Brawl + surge", None, True),
        (None, "surge, then bite", True),
        ("Strength+Brawl+surge", None, True),
        (None, "surged earlier", False),
        (None, "resurge", False),
        (None, "insurgent", False),
        (None, "no blood", False),
        (None, None, False),
    ],
)
async def test_surging(
    ctx: AppCtx, owner: discord.Member, pool_str: str | None, comment: str | None, expected: bool
):
    """Vampires surge when "surge" appears in the pool or comment."""
    roll = make_roll([6], [], pool_str=pool_str)
    display = make_display(ctx, owner, roll, comment=comment, character=make_char("vampire"))

    assert display.surging is expected


@pytest.mark.parametrize("splat", ["thin-blood", "ghoul"])
async def test_surging_other_splats(ctx: AppCtx, owner: discord.Member, splat: str):
    """Thin-bloods and ghouls can surge."""
    char = make_char(splat)
    display = make_display(ctx, owner, make_roll([6], []), comment="surge", character=char)

    assert display.surging


async def test_surging_mortal(ctx: AppCtx, owner: discord.Member):
    """Mortals never surge."""
    char = make_char("mortal")
    display = make_display(ctx, owner, make_roll([6], []), comment="surge", character=char)

    assert not display.surging


async def test_surging_no_character(ctx: AppCtx, owner: discord.Member):
    """Rolls without a character never surge."""
    display = make_display(ctx, owner, make_roll([6], []), comment="surge")

    assert not display.surging


async def test_surging_from_impairment_comment(ctx: AppCtx, owner: discord.Member):
    """Surge detection checks the comment as displayed, including impairment."""
    char = make_char("vampire")
    char.willpower = "xxxxx"
    display = make_display(ctx, owner, make_roll([6], []), comment="surge", character=char)

    assert display.surging


# Buttons (initial roll)

PRIMARY = discord.ButtonStyle.primary
SECONDARY = discord.ButtonStyle.secondary
DANGER = discord.ButtonStyle.danger


async def test_buttons_all_enabled(ctx: AppCtx, owner: discord.Member):
    """A messy crit with failures enables every strategy."""
    display = make_display(ctx, owner, make_roll([10, 2], [10], 1))

    assert (await show(display)).buttons == [
        ("Re-Roll Failures", PRIMARY, False, None),
        ("Max Crits", PRIMARY, False, None),
        ("Avoid Messy", PRIMARY, False, None),
        ("Risky Avoid", PRIMARY, False, None),
    ]


async def test_buttons_partially_disabled(ctx: AppCtx, owner: discord.Member):
    """Unavailable strategies are shown but disabled."""
    display = make_display(ctx, owner, make_roll([6, 6], []))

    assert (await show(display)).buttons == [
        ("Re-Roll Failures", PRIMARY, True, None),
        ("Max Crits", PRIMARY, False, None),
        ("Avoid Messy", PRIMARY, True, None),
        ("Risky Avoid", PRIMARY, True, None),
    ]


async def test_buttons_max_crits_disabled(ctx: AppCtx, owner: discord.Member):
    """Max Crits is disabled when it can't help, even if failures can be rerolled."""
    display = make_display(ctx, owner, make_roll([2], [5]))

    assert (await show(display)).buttons == [
        ("Re-Roll Failures", PRIMARY, False, None),
        ("Max Crits", PRIMARY, True, None),
        ("Avoid Messy", PRIMARY, True, None),
        ("Risky Avoid", PRIMARY, True, None),
    ]


async def test_buttons_all_disabled(ctx: AppCtx, owner: discord.Member):
    """With no useful strategy, all buttons are still shown, but disabled."""
    display = make_display(ctx, owner, make_roll([10], []))

    assert (await show(display)).buttons == [
        ("Re-Roll Failures", PRIMARY, True, None),
        ("Max Crits", PRIMARY, True, None),
        ("Avoid Messy", PRIMARY, True, None),
        ("Risky Avoid", PRIMARY, True, None),
    ]


async def test_buttons_wp_unavailable(ctx: AppCtx, owner: discord.Member):
    """Pools without Attributes or Skills can't use Willpower."""
    display = make_display(ctx, owner, make_roll([6, 2], [], pool_str="Hunger + Potence"))

    assert (await show(display)).buttons == [
        ("WP Unavailable (p.158)", SECONDARY, True, None),
    ]


async def test_buttons_with_surge(ctx: AppCtx, owner: discord.Member):
    """Surging adds Rouse buttons on the second row."""
    display = make_display(
        ctx, owner, make_roll([6, 2], []), comment="surge", character=make_char("vampire")
    )

    assert (await show(display)).buttons == [
        ("Re-Roll Failures", PRIMARY, False, None),
        ("Max Crits", PRIMARY, False, None),
        ("Avoid Messy", PRIMARY, True, None),
        ("Risky Avoid", PRIMARY, True, None),
        ("Rouse", DANGER, False, 1),
        ("Rouse w/ Reroll", DANGER, False, 1),
    ]


async def test_buttons_wp_unavailable_with_surge(ctx: AppCtx, owner: discord.Member):
    """Rouse buttons still appear when Willpower is unavailable."""
    roll = make_roll([6, 2], [], pool_str="Potence")
    display = make_display(ctx, owner, roll, comment="surge", character=make_char("vampire"))

    assert (await show(display)).buttons == [
        ("WP Unavailable (p.158)", SECONDARY, True, None),
        ("Rouse", DANGER, False, 1),
        ("Rouse w/ Reroll", DANGER, False, 1),
    ]


# Buttons (after reroll)


async def test_buttons_rerolled_no_character(ctx: AppCtx, owner: discord.Member):
    """Character-less rerolls have no buttons."""
    screen = await show(make_display(ctx, owner, make_roll([6, 2], [])))
    await reroll(screen)

    assert screen.buttons is not None
    assert all(disabled for _, _, disabled, _ in screen.buttons)
    assert not screen.listening


async def test_buttons_rerolled_with_character(ctx: AppCtx, owner: discord.Member):
    """Characters can mark Willpower after a reroll."""
    display = make_display(ctx, owner, make_roll([6, 2], []), character=make_char("vampire"))
    screen = await show(display)
    await reroll(screen)

    assert screen.buttons == [("Mark WP Use", PRIMARY, False, None)]


async def test_buttons_rerolled_with_surge(ctx: AppCtx, owner: discord.Member):
    """Unused surges remain available after a reroll, on the first row."""
    display = make_display(
        ctx, owner, make_roll([6, 2], []), comment="surge", character=make_char("vampire")
    )
    screen = await show(display)
    await reroll(screen)

    assert screen.buttons == [
        ("Mark WP Use", PRIMARY, False, None),
        ("Rouse", DANGER, False, None),
        ("Rouse w/ Reroll", DANGER, False, None),
    ]


async def test_buttons_rerolled_after_surging(ctx: AppCtx, owner: discord.Member):
    """Rouse buttons disappear once the surge is used."""
    display = make_display(
        ctx, owner, make_roll([6, 2], []), comment="surge", character=make_char("vampire")
    )
    screen = await show(display)
    await press_rouse(screen)
    await reroll(screen)

    assert screen.buttons == [("Mark WP Use", PRIMARY, False, None)]


# Interaction harness
#
# These helpers are the only code that knows how RollDisplay talks to Discord.
# Tests show a roll, press buttons by label, and check what the message looks
# like afterward. If RollDisplay's internals change, update the helpers, not
# the tests.


@dataclass
class Screen:
    """What Discord currently shows for a roll message."""

    display: RollDisplay
    embed: discord.Embed | None = None
    buttons: list[tuple] | None = None
    view: discord.ui.View | None = None
    ephemeral: list[str] = field(default_factory=list)

    def record(self, **kwargs: Any):
        """Apply a message send or edit. Omitted keys keep their current values."""
        if "embed" in kwargs:
            self.embed = kwargs["embed"]
        if "view" in kwargs:
            self.view = kwargs["view"]
            self.buttons = button_summary(self.view.children) if self.view else None

    def record_ephemeral(self, content: str, **_: Any):
        """Record an ephemeral reply to a button press."""
        self.ephemeral.append(content)

    @property
    def listening(self) -> bool:
        """Whether the shown buttons still respond to presses."""
        return self.view is not None and not self.view.is_finished()


def fake_interaction(screen: Screen, user: discord.Member | discord.User) -> AsyncMock:
    """Create an interaction whose responses update the screen."""
    ctx = screen.display.ctx
    inter = AsyncMock(spec=discord.Interaction)
    inter.user = user
    inter.guild = ctx.guild
    inter.channel = ctx.channel
    inter.response = AsyncMock(spec=discord.InteractionResponse)
    inter.response.edit_message.side_effect = screen.record
    inter.response.send_message.side_effect = screen.record_ephemeral
    inter.edit_original_response.side_effect = screen.record
    inter.edit.side_effect = screen.record
    return inter


async def show(display: RollDisplay) -> Screen:
    """Send the roll and return what's shown."""
    screen = Screen(display)
    original = fake_interaction(screen, display.owner)

    def respond(**kwargs: Any):
        screen.record(**kwargs)
        return original

    cast(AsyncMock, display.ctx.respond).side_effect = respond
    await display.display()
    return screen


async def press(screen: Screen, label: str, by: discord.Member | None = None):
    """Press the shown button with the given label (by default, as the roll's owner)."""
    assert screen.view is not None and screen.buttons is not None, "No buttons are shown"
    labels = [summary[0] for summary in screen.buttons]
    assert label in labels, f"{label!r} isn't shown; buttons are {labels}"
    index = labels.index(label)
    assert not screen.buttons[index][2], f"{label!r} is disabled"
    assert screen.listening, "The buttons are no longer listening"

    button = cast(Button, screen.view.children[index])
    inter = fake_interaction(screen, by or screen.display.owner)
    inter.data = {"custom_id": button.custom_id}

    # Mirrors py-cord's View dispatch, minus its error swallowing
    if await screen.view.interaction_check(inter):
        await button.callback(inter)
    else:
        await screen.view.on_check_failure(inter)


async def press_reroll_failures(screen: Screen, by: discord.Member | None = None):
    """Press Re-Roll Failures."""
    await press(screen, "Re-Roll Failures", by)


async def press_max_crits(screen: Screen, by: discord.Member | None = None):
    """Press Max Crits."""
    await press(screen, "Max Crits", by)


async def press_avoid_messy(screen: Screen, by: discord.Member | None = None):
    """Press Avoid Messy."""
    await press(screen, "Avoid Messy", by)


async def press_risky_avoid(screen: Screen, by: discord.Member | None = None):
    """Press Risky Avoid."""
    await press(screen, "Risky Avoid", by)


async def press_mark_wp(screen: Screen, by: discord.Member | None = None):
    """Press Mark WP Use."""
    await press(screen, "Mark WP Use", by)


async def press_rouse(screen: Screen, by: discord.Member | None = None):
    """Press Rouse."""
    await press(screen, "Rouse", by)


async def press_rouse_reroll(screen: Screen, by: discord.Member | None = None):
    """Press Rouse w/ Reroll."""
    await press(screen, "Rouse w/ Reroll", by)


async def reroll(screen: Screen):
    """Re-roll failures, turning them into 10s."""
    with patch("inconnu.d10", return_value=10):
        await press_reroll_failures(screen)


async def render(display: RollDisplay) -> discord.Embed:
    """Send the roll and return the embed shown."""
    screen = await show(display)
    assert screen.embed is not None
    return screen.embed


async def time_out(screen: Screen):
    """Let the shown buttons time out."""
    assert screen.view is not None, "No buttons are shown"
    await screen.view.on_timeout()


# Showing a roll


async def test_show_initial(ctx: AppCtx, owner: discord.Member):
    """The first send shows the embed and the reroll buttons."""
    screen = await show(make_display(ctx, owner, make_roll([6, 2], [], 2)))
    assert screen.embed is not None

    assert screen.embed.title == "FAILURE! (1)"
    assert screen.buttons == [
        ("Re-Roll Failures", PRIMARY, False, None),
        ("Max Crits", PRIMARY, False, None),
        ("Avoid Messy", PRIMARY, True, None),
        ("Risky Avoid", PRIMARY, True, None),
    ]
    assert screen.listening


async def test_show_all_disabled_stops_listening(ctx: AppCtx, owner: discord.Member):
    """If no button can be pressed, the buttons stop listening right away."""
    screen = await show(make_display(ctx, owner, make_roll([10], [])))

    assert not screen.listening


async def test_show_wp_unavailable_stops_listening(ctx: AppCtx, owner: discord.Member):
    """The lone WP Unavailable button doesn't listen."""
    screen = await show(make_display(ctx, owner, make_roll([6], [], pool_str="Potence")))

    assert not screen.listening


async def test_show_wp_unavailable_with_surge_listens(ctx: AppCtx, owner: discord.Member):
    """Rouse buttons keep the view listening when WP is unavailable."""
    roll = make_roll([6], [], pool_str="Potence")
    display = make_display(ctx, owner, roll, comment="surge", character=make_char("vampire"))
    screen = await show(display)

    assert screen.listening


# Ownership


async def test_press_by_non_owner(ctx: AppCtx, owner: discord.Member, intruder: discord.Member):
    """Only the roll's owner can press its buttons."""
    screen = await show(make_display(ctx, owner, make_roll([6, 2], [], 2)))
    buttons = screen.buttons

    await press_reroll_failures(screen, by=intruder)

    assert screen.ephemeral == ["This button doesn't belong to you!"]
    assert screen.embed is not None
    assert screen.embed.title == "FAILURE! (1)"
    assert screen.buttons == buttons
    assert screen.listening


# Rerolls


@pytest.mark.parametrize(
    "press_strategy,label,descriptor",
    [
        (press_reroll_failures, "Re-Roll Failures", "Rerolling Failures"),
        (press_max_crits, "Max Crits", "Maximizing Criticals"),
        (press_avoid_messy, "Avoid Messy", "Avoiding Messy Critical"),
        (press_risky_avoid, "Risky Avoid", "Avoid Messy (Risky)"),
    ],
)
async def test_reroll_without_character(
    ctx: AppCtx, owner: discord.Member, press_strategy: PressHelper, label: str, descriptor: str
):
    """Without a character, the pressed button grays out and all buttons are disabled."""
    screen = await show(make_display(ctx, owner, make_roll([10, 2], [10], 1)))

    with patch("inconnu.d10", return_value=5):
        await press_strategy(screen)

    assert screen.embed is not None and screen.embed.author is not None
    assert screen.embed.title is not None and screen.embed.title.startswith("R: ")
    assert screen.embed.author.name.endswith(descriptor)

    expected = [
        (lbl, SECONDARY if lbl == label else PRIMARY, True, None)
        for lbl in ("Re-Roll Failures", "Max Crits", "Avoid Messy", "Risky Avoid")
    ]
    assert screen.buttons == expected
    assert not screen.listening


async def test_reroll_with_character(ctx: AppCtx, owner: discord.Member):
    """With a character, the reroll buttons are replaced by Mark WP Use."""
    display = make_display(ctx, owner, make_roll([6, 2], [], 2), character=make_char("vampire"))
    screen = await show(display)

    with patch("inconnu.d10", return_value=10):
        await press_reroll_failures(screen)

    assert screen.embed is not None
    assert screen.embed.title == "R: SUCCESS! (2)"
    assert screen.buttons == [("Mark WP Use", PRIMARY, False, None)]
    assert screen.listening


async def test_reroll_with_character_surging(ctx: AppCtx, owner: discord.Member):
    """Unused surge buttons carry over after a reroll."""
    display = make_display(
        ctx, owner, make_roll([6, 2], [], 2), comment="surge", character=make_char("vampire")
    )
    screen = await show(display)

    with patch("inconnu.d10", return_value=10):
        await press_reroll_failures(screen)

    assert screen.buttons == [
        ("Mark WP Use", PRIMARY, False, None),
        ("Rouse", DANGER, False, None),
        ("Rouse w/ Reroll", DANGER, False, None),
    ]


@pytest.mark.parametrize("has_character", [False, True])
async def test_reroll_notifies_listener(ctx: AppCtx, owner: discord.Member, has_character: bool):
    """The listener receives the rerolled outcome."""
    char = make_char("vampire") if has_character else None
    roll = make_roll([6, 2], [], 2)
    listener = AsyncMock()
    screen = await show(make_display(ctx, owner, roll, character=char, listener=listener))

    with patch("inconnu.d10", return_value=10):
        await press_reroll_failures(screen)

    listener.assert_awaited_once_with(ANY, char, roll)


# Willpower


async def test_mark_wp(
    ctx: AppCtx, owner: discord.Member, mock_char_save: AsyncMock, mock_char_display: AsyncMock
):
    """Marking WP adds Superficial Willpower damage and disables the button."""
    char = make_char("vampire")
    screen = await show(make_display(ctx, owner, make_roll([6, 2], [], 2), character=char))
    with patch("inconnu.d10", return_value=10):
        await press_reroll_failures(screen)

    await press_mark_wp(screen)

    assert char.superficial_wp == 1
    mock_char_save.assert_awaited_once()
    mock_char_display.assert_awaited_once_with(
        ANY, char, title="Willpower Spent", owner=owner, fields=ANY
    )
    assert screen.embed is not None
    assert screen.embed.title == "R: SUCCESS! (2)"
    assert screen.buttons == [("Mark WP Use", SECONDARY, True, None)]


# Surging


@pytest.mark.parametrize(
    "press_surge,oblivion",
    [(press_rouse, False), (press_rouse_reroll, True)],
)
async def test_surge(
    ctx: AppCtx,
    owner: discord.Member,
    mock_rouse: AsyncMock,
    press_surge: PressHelper,
    oblivion: bool,
):
    """Surging Rouses once and disables both surge buttons."""
    char = make_char("vampire")
    display = make_display(ctx, owner, make_roll([6, 2], [], 2), comment="surge", character=char)
    screen = await show(display)

    await press_surge(screen)

    mock_rouse.assert_awaited_once_with(ANY, char, 1, "Surge", oblivion)
    assert screen.buttons == [
        ("Re-Roll Failures", PRIMARY, False, None),
        ("Max Crits", PRIMARY, False, None),
        ("Avoid Messy", PRIMARY, True, None),
        ("Risky Avoid", PRIMARY, True, None),
        ("Rouse", SECONDARY, True, 1),
        ("Rouse w/ Reroll", SECONDARY, True, 1),
    ]
    assert screen.listening


async def test_surge_then_reroll(ctx: AppCtx, owner: discord.Member):
    """Used surges don't come back after a reroll."""
    display = make_display(
        ctx, owner, make_roll([6, 2], [], 2), comment="surge", character=make_char("vampire")
    )
    screen = await show(display)

    await press_rouse(screen)
    with patch("inconnu.d10", return_value=10):
        await press_reroll_failures(screen)

    assert screen.buttons == [("Mark WP Use", PRIMARY, False, None)]


async def test_reroll_then_surge(ctx: AppCtx, owner: discord.Member, mock_rouse: AsyncMock):
    """Surging after a reroll leaves Mark WP Use available."""
    char = make_char("vampire")
    display = make_display(ctx, owner, make_roll([6, 2], [], 2), comment="surge", character=char)
    screen = await show(display)

    with patch("inconnu.d10", return_value=10):
        await press_reroll_failures(screen)
    await press_rouse(screen)

    mock_rouse.assert_awaited_once_with(ANY, char, 1, "Surge", False)
    assert screen.buttons == [
        ("Mark WP Use", PRIMARY, False, None),
        ("Rouse", SECONDARY, True, None),
        ("Rouse w/ Reroll", SECONDARY, True, None),
    ]


# Timeouts


async def test_timeout(ctx: AppCtx, owner: discord.Member):
    """Timing out disables the buttons and reports the final outcome."""
    roll = make_roll([6, 2], [], 2)
    handler = AsyncMock()
    screen = await show(make_display(ctx, owner, roll, timeout=handler))

    await time_out(screen)

    assert screen.buttons == [
        ("Re-Roll Failures", PRIMARY, True, None),
        ("Max Crits", PRIMARY, True, None),
        ("Avoid Messy", PRIMARY, True, None),
        ("Risky Avoid", PRIMARY, True, None),
    ]
    handler.assert_awaited_once_with(roll)


async def test_timeout_after_reroll(ctx: AppCtx, owner: discord.Member):
    """Post-reroll buttons are disabled on timeout, and the handler gets the new outcome."""
    roll = make_roll([6, 2], [], 2)
    handler = AsyncMock()
    display = make_display(ctx, owner, roll, character=make_char("vampire"), timeout=handler)
    screen = await show(display)
    with patch("inconnu.d10", return_value=10):
        await press_reroll_failures(screen)

    await time_out(screen)

    assert screen.buttons == [("Mark WP Use", PRIMARY, True, None)]
    handler.assert_awaited_once_with(roll)
    assert roll.is_successful


# Stats


async def test_stats_logged(ctx: AppCtx, owner: discord.Member, mock_log_roll: AsyncMock):
    """The first display logs the message ID; rerolls log without one."""
    roll = make_roll([6, 2], [], 2)
    screen = await show(make_display(ctx, owner, roll, comment="Hi"))

    mock_log_roll.assert_awaited_once_with(2, 3, owner.id, MESSAGE_ID, None, roll, "Hi")

    with patch("inconnu.d10", return_value=10):
        await press_reroll_failures(screen)

    assert mock_log_roll.await_count == 2
    mock_log_roll.assert_awaited_with(2, 3, owner.id, None, None, roll, "Hi")


async def test_stats_logged_in_dm(
    ctx: AppCtx, owner: discord.Member, mock_log_roll: AsyncMock, mock_get_message: AsyncMock
):
    """DM rolls are logged without guild, channel, or message IDs."""
    cast(MagicMock, ctx).guild = None
    roll = make_roll([6, 2], [], 2)
    await show(make_display(ctx, owner, roll))

    mock_log_roll.assert_awaited_once_with(None, None, owner.id, None, None, roll, None)
    mock_get_message.assert_not_awaited()
