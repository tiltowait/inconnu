"""Tests for interface/help.py's generated help pages and persistent menu."""

from collections.abc import Generator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest

from bot import InconnuBot
from ctx import AppCtx
from interface.help import (
    HELP_MENU_ID,
    OVERVIEW,
    Help,
    HelpMenu,
    HelpView,
    _section_options,
    help_cogs,
    help_page,
    resolve_section,
    section_descriptions,
)

SECTIONS = [
    "Characters",
    "Experience",
    "Gameplay",
    "Headers",
    "Macros",
    "Miscellaneous",
    "Reference",
    "Roleposting",
    "Settings",
    "Traits",
]


@pytest.fixture(scope="module")
def bot() -> Generator[InconnuBot]:
    """A real InconnuBot with every cog loaded, logged in as a mock user, whose
    command mentions use the command's name."""
    me = MagicMock(spec=discord.ClientUser)
    me.display_name = "Inconnu"
    me.display_avatar.url = "https://example.com/avatar.png"

    with (
        patch.object(InconnuBot, "me", new_callable=PropertyMock, return_value=me),
        patch.object(InconnuBot, "cmd_mention", lambda _, name: f"</{name}:1>"),
    ):
        yield InconnuBot(intents=discord.Intents.none())


def all_text(embed: discord.Embed) -> str:
    """An embed's description and field values, joined."""
    return "\n".join([embed.description or "", *(str(f.value) for f in embed.fields)])


def test_sections(bot: InconnuBot):
    """Every cog with commands gets a section, except the hidden ones."""
    assert list(help_cogs(bot)) == SECTIONS


def test_sections_with_debug_guilds():
    """Debug guilds, which py-cord assigns to every command, don't hide sections."""
    debug_bot = InconnuBot(intents=discord.Intents.none(), debug_guilds=[1])
    assert list(help_cogs(debug_bot)) == SECTIONS


@pytest.mark.parametrize("section", [OVERVIEW, "Characters", "Gameplay", "Traits", "Roleposting"])
def test_pages_fit_discord_limits(bot: InconnuBot, section: str):
    """Pages stay within Discord's embed limits."""
    embed = help_page(bot, section)

    assert len(embed) <= 6000
    assert len(embed.description or "") <= 4096
    assert all(len(str(field.value)) <= 1024 for field in embed.fields)


def test_cog_page_lists_commands(bot: InconnuBot):
    """A cog page has the cog's description and mentions top-level commands and
    nested subcommands alike."""
    embed = help_page(bot, "Characters")
    text = all_text(embed)

    assert embed.title == "Characters"
    assert text.startswith("Create, display, and update your characters.")
    assert "* </character display:1>: " in text
    assert "* </character image upload:1>: " in text
    assert "* </vm:1>: " in all_text(help_page(bot, "Macros"))


def test_cog_page_lists_context_commands(bot: InconnuBot):
    """User and message commands are listed by where to right-click."""
    characters = help_page(bot, "Characters")
    roleplay = help_page(bot, "Roleposting")

    assert characters.fields[0].name == "Apps"
    assert characters.fields[0].value == "**Right-click a member:** Convictions, Profile, Stats"
    assert roleplay.fields[0].value == "**Right-click a message:** Post: Delete, Post: Edit"


def test_admin_commands_hidden(bot: InconnuBot):
    """Admin commands don't appear anywhere."""
    text = "\n".join(all_text(help_page(bot, section)) for section in help_cogs(bot))

    assert "</motd:1>" in text
    assert "announce" not in text
    assert "wizards" not in text


def test_overview_mentions_commands(bot: InconnuBot):
    """The hand-written overview's `/command` strings become mentions."""
    embed = help_page(bot, OVERVIEW)

    assert embed.title == "Commands Help"
    assert "</rouse:1>" in all_text(embed)


def test_unknown_section_shows_overview(bot: InconnuBot):
    """A section that no longer exists, such as from an old message, falls back
    to the overview."""
    assert help_page(bot, "Removed Cog").title == "Commands Help"


async def test_view_is_persistent(bot: InconnuBot):
    """The menu survives restarts: no timeout and a fixed custom ID."""
    view = HelpView(bot)
    menu = cast(HelpMenu, view.children[0])

    assert view.is_persistent()
    assert menu.custom_id == HELP_MENU_ID
    assert [o.label for o in menu.options] == [OVERVIEW, *help_cogs(bot)]
    assert [o.label for o in menu.options if o.default] == [OVERVIEW]


async def test_selecting_section_shows_page(bot: InconnuBot):
    """Selecting a section shows its page and keeps it selected."""
    menu = cast(HelpMenu, HelpView(bot).children[0])
    interaction = MagicMock(spec=discord.Interaction)
    interaction.client = bot
    interaction.response.edit_message = AsyncMock()

    with patch.object(HelpMenu, "values", new_callable=PropertyMock, return_value=["Macros"]):
        await menu.callback(interaction)

    kwargs = interaction.response.edit_message.call_args.kwargs
    new_menu = cast(HelpMenu, kwargs["view"].children[0])
    assert kwargs["embed"].title == "Macros"
    assert [o.label for o in new_menu.options if o.default] == ["Macros"]


@pytest.mark.parametrize(
    "name,expected",
    [("Traits", "Traits"), ("traits", "Traits"), ("Overview", OVERVIEW), ("Nope", OVERVIEW)],
)
def test_resolve_section(bot: InconnuBot, name: str, expected: str):
    """Section names match regardless of case; unknown names give the overview."""
    assert resolve_section(bot, name) == expected


async def test_section_autocomplete(bot: InconnuBot):
    """Autocomplete offers the sections containing what's been typed."""
    ctx = MagicMock(spec=discord.AutocompleteContext)
    ctx.bot = bot
    ctx.value = "RO"

    assert await _section_options(ctx) == ["Macros", "Roleposting"]


async def test_help_command_opens_section(bot: InconnuBot):
    """/help section: opens that section with it selected in the menu."""
    ctx = MagicMock(spec=AppCtx)
    ctx.respond = AsyncMock()
    cog = cast(Help, bot.get_cog("Help"))

    await cog.help_command.callback(cog, ctx, "macros")

    kwargs = ctx.respond.call_args.kwargs
    menu = cast(HelpMenu, kwargs["view"].children[0])
    assert kwargs["embed"].title == "Macros"
    assert [o.label for o in menu.options if o.default] == ["Macros"]


async def test_menu_descriptions(bot: InconnuBot):
    """Each menu option has a subtitle within Discord's 100-character limit."""
    menu = cast(HelpMenu, HelpView(bot).children[0])

    assert [o.description for o in menu.options] == list(section_descriptions(bot).values())
    assert all(0 < len(o.description or "") <= 100 for o in menu.options)
