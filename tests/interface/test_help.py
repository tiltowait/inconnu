"""Tests for interface/help.py's generated help pages and persistent menu."""

from collections.abc import Generator
from typing import cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest

from bot import InconnuBot
from ctx import AppCtx
from interface import CommandCog
from interface.help import HELP_MENU_ID, OVERVIEW, Help, HelpMenu, HelpView

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
def help_cog() -> Generator[Help]:
    """The Help cog of a real InconnuBot with every cog loaded, logged in as a mock
    user, whose command mentions use the command's name."""
    me = MagicMock(spec=discord.ClientUser)
    me.display_name = "Inconnu"
    me.display_avatar.url = "https://example.com/avatar.png"

    with (
        patch.object(InconnuBot, "me", new_callable=PropertyMock, return_value=me),
        patch.object(InconnuBot, "cmd_mention", lambda _, name: f"</{name}:1>"),
    ):
        bot = InconnuBot(intents=discord.Intents.none())
        yield cast(Help, bot.get_cog("Help"))


def all_text(embed: discord.Embed) -> str:
    """An embed's description and field values, joined."""
    return "\n".join([embed.description or "", *(str(f.value) for f in embed.fields)])


def test_sections(help_cog: Help):
    """Every cog with commands gets a section, except the hidden ones."""
    assert list(help_cog.help_cogs()) == SECTIONS


def test_sections_with_debug_guilds():
    """Debug guilds, which py-cord assigns to every command, don't hide sections."""
    debug_bot = InconnuBot(intents=discord.Intents.none(), debug_guilds=[1])
    assert list(cast(Help, debug_bot.get_cog("Help")).help_cogs()) == SECTIONS


@pytest.mark.parametrize("section", [OVERVIEW, "Characters", "Gameplay", "Traits", "Roleposting"])
def test_pages_fit_discord_limits(help_cog: Help, section: str):
    """Pages stay within Discord's embed limits."""
    embed = help_cog.help_page(section)

    assert len(embed) <= 6000
    assert len(embed.description or "") <= 4096
    assert all(len(str(field.value)) <= 1024 for field in embed.fields)


def test_cog_page_lists_commands(help_cog: Help):
    """A cog page has the cog's description and mentions top-level commands and
    nested subcommands alike."""
    embed = help_cog.help_page("Characters")
    text = all_text(embed)

    assert embed.title == "Characters"
    assert text.startswith("Create, display, and update your characters.")
    assert "* </character display:1>: " in text
    assert "* </character image upload:1>: " in text
    assert "* </vm:1>: " in all_text(help_cog.help_page("Macros"))


def test_cog_page_lists_context_commands(help_cog: Help):
    """User and message commands are listed by where to right-click."""
    characters = help_cog.help_page("Characters")
    roleplay = help_cog.help_page("Roleposting")

    assert characters.fields[0].name == "Apps"
    assert characters.fields[0].value == "**Right-click a member:** Convictions, Profile, Stats"
    assert roleplay.fields[0].value == "**Right-click a message:** Post: Delete, Post: Edit"


def test_admin_commands_hidden(help_cog: Help):
    """Admin commands don't appear anywhere."""
    text = "\n".join(all_text(help_cog.help_page(s)) for s in help_cog.help_sections())

    assert "</motd:1>" in text
    assert "announce" not in text
    assert "wizards" not in text


def test_overview_mentions_commands(help_cog: Help):
    """The hand-written overview's `/command` strings become mentions."""
    embed = help_cog.help_page(OVERVIEW)

    assert embed.title == "Basic Overview"
    assert "</rouse:1>" in all_text(embed)


def test_unknown_section_shows_overview(help_cog: Help):
    """A section that no longer exists, such as from an old message, falls back
    to the overview."""
    assert help_cog.help_page("Removed Cog").title == "Basic Overview"


async def test_view_is_persistent(help_cog: Help):
    """The menu survives restarts: no timeout and a fixed custom ID."""
    view = HelpView(help_cog)
    menu = cast(HelpMenu, view.children[0])

    assert view.is_persistent()
    assert menu.custom_id == HELP_MENU_ID
    assert [o.label for o in menu.options] == help_cog.help_sections()
    assert [o.label for o in menu.options if o.default] == [OVERVIEW]


async def test_selecting_section_shows_page(help_cog: Help):
    """Selecting a section shows its page and keeps it selected."""
    menu = cast(HelpMenu, HelpView(help_cog).children[0])
    interaction = MagicMock(spec=discord.Interaction)
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
def test_resolve_section(help_cog: Help, name: str, expected: str):
    """Section names match regardless of case; unknown names give the overview."""
    assert help_cog.resolve_section(name) == expected


async def test_section_autocomplete(help_cog: Help):
    """Autocomplete offers the sections containing what's been typed."""
    ctx = MagicMock(spec=discord.AutocompleteContext)
    ctx.value = "RO"

    assert await help_cog._section_options(ctx) == ["Macros", "Roleposting"]


async def test_help_command_opens_section(help_cog: Help):
    """/help section: opens that section with it selected in the menu."""
    ctx = MagicMock(spec=AppCtx)
    ctx.respond = AsyncMock()

    await help_cog.help_command.callback(help_cog, ctx, "macros")

    kwargs = ctx.respond.call_args.kwargs
    menu = cast(HelpMenu, kwargs["view"].children[0])
    assert kwargs["embed"].title == "Macros"
    assert [o.label for o in menu.options if o.default] == ["Macros"]


async def test_menu_descriptions(help_cog: Help):
    """Each menu option has a subtitle within Discord's 100-character limit."""
    menu = cast(HelpMenu, HelpView(help_cog).children[0])

    assert [o.description for o in menu.options] == list(help_cog.section_descriptions().values())
    assert all(0 < len(o.description or "") <= 100 for o in menu.options)


def test_cogs_with_commands_are_command_cogs(help_cog: Help):
    """Every cog with commands, besides the admin and help cogs, is a CommandCog,
    so it gets a help page."""
    uncovered = [
        name
        for name, cog in help_cog.bot.cogs.items()
        if cog.get_commands()
        and name not in {"AdminCog", "Help"}
        and not isinstance(cog, CommandCog)
    ]
    assert not uncovered


def test_command_cogs_link_docs(help_cog: Help):
    """Every command cog links to its docs."""
    assert all(cog.docs for cog in help_cog.help_cogs().values())


async def test_view_links_section_docs(help_cog: Help):
    """A cog page's view links to that cog's docs above the support links. The
    overview has only the support links."""

    def links(view: HelpView) -> list[tuple[str | None, int | None]]:
        """The view's link buttons' labels and rows."""
        return [(b.label, b.row) for b in view.children if isinstance(b, discord.ui.Button)]

    assert links(HelpView(help_cog, "Gameplay"))[:2] == [("Rolls", 1), ("Gameplay Shortcuts", 1)]
    assert [row for _, row in links(HelpView(help_cog, "Gameplay"))[2:]] == [2, 2, 2]
    assert [row for _, row in links(HelpView(help_cog))] == [2, 2, 2]
