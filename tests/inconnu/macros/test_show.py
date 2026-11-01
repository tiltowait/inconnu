"""Tests for inconnu/macros/show.py's paginated macro display."""

from dataclasses import dataclass
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ui import Button

import errors
from bot import InconnuBot
from ctx import AppCtx
from inconnu.macros.show import show
from models import VChar
from models.vchardocs import VCharMacro
from tests.characters import gen_char
from ui.views import PagedView

AVATAR = "https://example.com/avatar.png"
PROFILE_IMAGE = "https://example.com/profile.png"
PREV = "◀️"
NEXT = "▶️"


@pytest.fixture
def owner() -> discord.Member:
    """The macros' owner."""
    member = MagicMock(spec=discord.Member)
    member.guild_avatar = None
    member.display_avatar = MagicMock(spec=discord.Asset)
    member.display_avatar.url = AVATAR
    return member


@pytest.fixture
def ctx(owner: discord.Member) -> AppCtx:
    """The /macro list invocation."""
    ctx = MagicMock(spec=AppCtx)
    ctx.user = owner
    ctx.bot = MagicMock(spec=InconnuBot)
    ctx.bot.cmd_mention.side_effect = lambda name: f"</{name}:1>"
    ctx.respond = AsyncMock()  # A property on ApplicationContext, so the spec can't infer it
    return ctx


@pytest.fixture
def character() -> VChar:
    """A PC with no macros."""
    char = gen_char("vampire")
    char.user = 1  # gen_char's user matches SPC_OWNER
    char.name = "Nadea Theron"
    return char


def make_macro(name: str, **kwargs: Any) -> VCharMacro:
    """Create a macro with sensible defaults."""
    fields: dict[str, Any] = {
        "name": name,
        "pool": ["strength", "brawl"],
        "hunger": True,
        "difficulty": 0,
        "rouses": 0,
        "reroll_rouses": False,
        "staining": "show",
        "hunt": False,
        "comment": None,
    }
    fields.update(kwargs)
    return VCharMacro(**fields)


@dataclass
class Screen:
    """What Discord currently shows for the macro list."""

    view: PagedView
    ephemeral: bool

    @property
    def components(self) -> list[dict[str, Any]]:
        """The message's top-level components."""
        return self.view.to_components()

    @property
    def containers(self) -> list[dict[str, Any]]:
        """The current page's macro containers."""
        container = discord.ComponentType.container.value
        return [item for item in self.components if item["type"] == container]

    @property
    def header(self) -> dict[str, Any]:
        """The page's header section."""
        return self.components[0]

    @property
    def macros(self) -> list[str]:
        """The text of each macro container on the page."""
        texts = []
        for container in self.containers:
            items = container["components"]
            assert len(items) == 1
            assert items[0]["type"] == discord.ComponentType.text_display.value
            texts.append(items[0]["content"])
        return texts

    @property
    def buttons(self) -> list[tuple[str | None, str | None, bool]] | None:
        """The page controls as (emoji, label, disabled), if shown."""
        controls = self.components[-1]
        if controls["type"] != discord.ComponentType.action_row.value:
            return None
        return [
            (button.get("emoji", {}).get("name"), button.get("label"), button["disabled"])
            for button in controls["components"]
        ]


async def show_macros(ctx: AppCtx, character: VChar) -> Screen:
    """Run /macro list and return what's shown."""
    await show(ctx, character)
    kwargs = cast(AsyncMock, ctx.respond).call_args.kwargs
    return Screen(kwargs["view"], kwargs.get("ephemeral", False))


async def press(screen: Screen, emoji: str):
    """Press the page control with the given emoji."""
    buttons = screen.buttons
    assert buttons is not None, "No page controls are shown"
    emojis = [summary[0] for summary in buttons]
    assert emoji in emojis, f"{emoji!r} isn't shown; buttons are {emojis}"
    index = emojis.index(emoji)
    assert not buttons[index][2], f"{emoji!r} is disabled"

    button = cast(Button, screen.view.children[-1].children[index])  # type: ignore[attr-defined]
    inter = AsyncMock(spec=discord.Interaction)
    await button.callback(inter)
    inter.edit.assert_awaited_once_with(view=screen.view)


# Errors


async def test_no_macros(ctx: AppCtx, character: VChar):
    """A character without macros is refused."""
    with pytest.raises(errors.MacroError, match="Nadea Theron has no macros!"):
        await show(ctx, character)
    cast(AsyncMock, ctx.respond).assert_not_awaited()


# Layout


async def test_single_page(ctx: AppCtx, character: VChar):
    """A short list is one ephemeral page without page controls."""
    character.macros = [make_macro("hunt"), make_macro("brawl")]
    screen = await show_macros(ctx, character)

    assert screen.ephemeral
    assert screen.buttons is None
    assert [text.splitlines()[0] for text in screen.macros] == ["### HUNT", "### BRAWL"]


async def test_header(ctx: AppCtx, character: VChar):
    """The header names the character and links the macro commands."""
    character.macros = [make_macro("hunt")]
    screen = await show_macros(ctx, character)
    header = screen.header

    assert header["type"] == discord.ComponentType.section.value
    text = header["components"][0]["content"]
    assert text.startswith("## Macros: Nadea Theron\n")
    assert "Roll: </vm:1>" in text
    assert "Create: </macro create:1>" in text
    assert "Update: </macro update:1>" in text
    assert "Delete: </macro delete:1>" in text


async def test_thumbnail_avatar(ctx: AppCtx, character: VChar):
    """Without a profile image, the thumbnail is the user's avatar."""
    character.macros = [make_macro("hunt")]
    screen = await show_macros(ctx, character)

    assert screen.header["accessory"]["media"]["url"] == AVATAR


async def test_thumbnail_profile_image(ctx: AppCtx, character: VChar):
    """A character's profile image takes precedence over the avatar."""
    character.macros = [make_macro("hunt")]
    character.profile.images = [PROFILE_IMAGE]
    screen = await show_macros(ctx, character)

    assert screen.header["accessory"]["media"]["url"] == PROFILE_IMAGE


async def test_container_per_macro(ctx: AppCtx, character: VChar):
    """The header stands alone, and each macro has its own container."""
    character.macros = [make_macro("hunt"), make_macro("brawl")]
    screen = await show_macros(ctx, character)

    assert len(screen.components) == 3
    assert len(screen.containers) == 2


# Macro text


async def test_macro_text_defaults(ctx: AppCtx, character: VChar):
    """A macro with default settings shows only its pool."""
    character.macros = [make_macro("brawl")]
    screen = await show_macros(ctx, character)

    assert screen.macros == ["### BRAWL\n`strength brawl`"]


async def test_macro_text(ctx: AppCtx, character: VChar):
    """Non-default settings go below the pool, and the comment below a blank
    line."""
    character.macros = [make_macro("brawl", difficulty=3, hunt=True, comment="Punch")]
    screen = await show_macros(ctx, character)

    assert screen.macros == ["### BRAWL\n`strength brawl`\nDifficulty 3 · Hunt\n-# \u200b\n-# Punch"]


async def test_macro_text_with_rouses(ctx: AppCtx, character: VChar):
    """A macro with Rouse checks shows rerolls and staining."""
    character.macros = [
        make_macro(
            "surge",
            pool=[],
            hunger=False,
            rouses=2,
            reroll_rouses=True,
            staining="apply",
        )
    ]
    screen = await show_macros(ctx, character)

    assert screen.macros == [
        "### SURGE\n2 Rouse Checks (rerolled) · Stains · No Hunger"
    ]


async def test_macro_text_empty(ctx: AppCtx, character: VChar):
    """A macro with no pool and default settings shows only its name."""
    character.macros = [make_macro("nothing", pool=[])]
    screen = await show_macros(ctx, character)

    assert screen.macros == ["### NOTHING"]


# Pagination


@pytest.fixture
def three_pages(character: VChar) -> VChar:
    """A character whose macros are long enough to need a page each."""
    character.macros = [make_macro(name, comment="x" * 1200) for name in ("one", "two", "three")]
    return character


def page_macro(screen: Screen) -> str:
    """The name line of the page's only macro."""
    assert len(screen.macros) == 1
    return screen.macros[0].splitlines()[0]


async def test_first_page(ctx: AppCtx, three_pages: VChar):
    """A long list starts on the first page, with Previous disabled."""
    screen = await show_macros(ctx, three_pages)

    assert page_macro(screen) == "### ONE"
    assert screen.buttons == [(PREV, None, True), (None, "1/3", True), (NEXT, None, False)]


async def test_next_page(ctx: AppCtx, three_pages: VChar):
    """Next shows the following page and enables Previous."""
    screen = await show_macros(ctx, three_pages)
    await press(screen, NEXT)

    assert page_macro(screen) == "### TWO"
    assert screen.buttons == [(PREV, None, False), (None, "2/3", True), (NEXT, None, False)]


async def test_last_page(ctx: AppCtx, three_pages: VChar):
    """The last page disables Next."""
    screen = await show_macros(ctx, three_pages)
    await press(screen, NEXT)
    await press(screen, NEXT)

    assert page_macro(screen) == "### THREE"
    assert screen.buttons == [(PREV, None, False), (None, "3/3", True), (NEXT, None, True)]


async def test_previous_page(ctx: AppCtx, three_pages: VChar):
    """Previous goes back a page."""
    screen = await show_macros(ctx, three_pages)
    await press(screen, NEXT)
    await press(screen, NEXT)
    await press(screen, PREV)

    assert page_macro(screen) == "### TWO"
    assert screen.buttons == [(PREV, None, False), (None, "2/3", True), (NEXT, None, False)]


async def test_every_macro_shown_once(ctx: AppCtx, character: VChar):
    """Paging through a long list shows each macro exactly once, in order."""
    names = [f"macro{i}" for i in range(20)]
    character.macros = [make_macro(name) for name in names]
    screen = await show_macros(ctx, character)

    seen = [text.splitlines()[0] for text in screen.macros]
    while screen.buttons is not None and not screen.buttons[2][2]:
        await press(screen, NEXT)
        seen += [text.splitlines()[0] for text in screen.macros]

    assert screen.buttons is not None, "20 macros should need several pages"
    assert seen == [f"### {name.upper()}" for name in names]


async def test_macro_count_per_page(ctx: AppCtx, character: VChar):
    """Short macros are capped at 10 per page, to stay within Discord's
    component limit."""
    character.macros = [make_macro(f"m{i}", pool=[]) for i in range(25)]
    screen = await show_macros(ctx, character)

    counts = [len(screen.macros)]
    while screen.buttons is not None and not screen.buttons[2][2]:
        await press(screen, NEXT)
        counts.append(len(screen.macros))

    assert counts == [10, 10, 5]
