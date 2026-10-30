"""interface/help.py - Help commands"""

from typing import TYPE_CHECKING

import discord
from discord import option
from discord.commands import (
    ContextMenuCommand,
    SlashCommand,
    SlashCommandGroup,
    UserCommand,
    slash_command,
)
from discord.ext import commands
from discord.ui import Button, Select, View

from constants import PATREON, SUPPORT_URL
from ctx import AppCtx
from utils import cmd_replace_respond
from utils.cmdreplace import mention_embed_commands
from utils.urls import docs_url, web_asset

if TYPE_CHECKING:
    from bot import InconnuBot

HELP_MENU_ID = "help-menu"
OVERVIEW = "Overview"
OVERVIEW_DESCRIPTION = "Rolling basics and common commands."

# Cogs left out of the help menu, by qualified name
HIDDEN_COGS = frozenset({"AdminCog", "Help"})


def support_buttons(row: int | None = None) -> list[Button]:
    """Link buttons to the quickstart guide, support server, and Patreon."""
    return [
        Button(label="New? Click here!", url=docs_url("guides/quickstart"), row=row),
        Button(label="Server", url=SUPPORT_URL, row=row),
        Button(label="Patreon", url=PATREON, row=row),
    ]


def _slash_commands(cog: discord.Cog) -> list[SlashCommand]:
    """The cog's slash commands, including subcommands, sorted by name."""
    found: list[SlashCommand] = []
    for command in cog.get_commands():
        if isinstance(command, SlashCommandGroup):
            found.extend(c for c in command.walk_commands() if isinstance(c, SlashCommand))
        elif isinstance(command, SlashCommand):
            found.append(command)

    return sorted(found, key=lambda c: c.qualified_name)


def _context_commands(cog: discord.Cog) -> list[ContextMenuCommand]:
    """The cog's user and message commands."""
    return [c for c in cog.get_commands() if isinstance(c, ContextMenuCommand)]


class HelpMenu(Select["HelpView"]):
    """The help section selector. Stateless, so it keeps working across restarts."""

    def __init__(self, help_cog: Help, selected: str):
        super().__init__(
            custom_id=HELP_MENU_ID,
            placeholder="Select help section",
            options=[
                discord.SelectOption(
                    label=section, description=description, default=section == selected
                )
                for section, description in help_cog.section_descriptions().items()
            ],
        )
        self.help_cog = help_cog

    async def callback(self, interaction: discord.Interaction):
        """Show the selected section."""
        section = self.values[0] if self.values else OVERVIEW
        await interaction.response.edit_message(
            embed=self.help_cog.help_page(section), view=HelpView(self.help_cog, section)
        )


class HelpView(View):
    """The persistent help menu, plus support links."""

    def __init__(self, help_cog: Help, selected: str = OVERVIEW):
        super().__init__(timeout=None)
        self.add_item(HelpMenu(help_cog, selected))
        for button in support_buttons(row=1):
            self.add_item(button)


class Help(commands.Cog):
    """A class for housing the /help command."""

    def __init__(self, bot: InconnuBot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        """Register the persistent help menu."""
        if not self.bot.persistent_views_added:
            self.bot.add_view(HelpView(self))
            self.bot.persistent_views_added = True

    async def _section_options(self, ctx: discord.AutocompleteContext) -> list[str]:
        """The help sections containing what the user has typed."""
        typed = (ctx.value or "").casefold()
        return [s for s in self.help_sections() if typed in s.casefold()]

    @slash_command(name="help")
    @option(
        "section",
        description="The help section to show",
        autocomplete=_section_options,
        default=OVERVIEW,
    )
    async def help_command(self, ctx: AppCtx, section: str):
        """See the bot's commands and how to use them."""
        section = self.resolve_section(section)
        await ctx.respond(embed=self.help_page(section), view=HelpView(self, section))

    @slash_command()
    async def info(self, ctx: AppCtx):
        """Display bot info."""
        embed = discord.Embed(
            title="Bot Information",
            description="**Inconnu** is a dice roller for Vampire: The Masquerade 5th Edition.",
        )
        embed.set_author(name=self.bot.me.display_name, icon_url=self.bot.me.avatar)
        embed.set_thumbnail(url=web_asset("darkpack_logo2.webp"))

        embed.add_field(name="Author", value="`@tiltowait#8282`", inline=False)
        embed.add_field(
            name="Source code", value="[GitHub](https://github.com/tiltowait/inconnu)", inline=False
        )
        embed.add_field(name="License", value="MIT", inline=False)

        embed.set_footer(
            text=(
                "Portions of the materials are the copyrights and trademarks "
                "of Paradox Interactive AB, and are used with permission. All "
                "rights reserved. For more information please visit "
                "worldofdarkness.com."
            )
        )

        await cmd_replace_respond(ctx, embed=embed, view=View(*support_buttons(), timeout=None))

    # Pages

    def help_cogs(self) -> dict[str, discord.Cog]:
        """The cogs with a help page, by name, in menu order."""
        return {
            name: cog
            for name, cog in sorted(self.bot.cogs.items())
            if name not in HIDDEN_COGS and (_slash_commands(cog) or _context_commands(cog))
        }

    def help_sections(self) -> list[str]:
        """The help sections, in menu order."""
        return [OVERVIEW, *self.help_cogs()]

    def resolve_section(self, name: str) -> str:
        """The help section matching the name, ignoring case. Unknown names resolve
        to the overview."""
        folded = name.casefold()
        return next((s for s in self.help_sections() if s.casefold() == folded), OVERVIEW)

    def section_descriptions(self) -> dict[str, str]:
        """The help sections' menu subtitles, by section, in menu order."""
        return {
            OVERVIEW: OVERVIEW_DESCRIPTION,
            **{name: cog.description for name, cog in self.help_cogs().items()},
        }

    def help_page(self, section: str) -> discord.Embed:
        """The page for a help section. Unknown sections show the overview."""
        if cog := self.help_cogs().get(section):
            embed = self.cog_page(cog)
        else:
            embed = self.overview_page()
        mention_embed_commands(self.bot, embed)
        return embed

    def overview_page(self) -> discord.Embed:
        """The hand-written overview page."""
        embed = self._base_embed(
            title="Basic Overview",
            description=(
                f"Thank you for using {self.bot.me.mention}! This page "
                "gives a quick overview of the most important commands. See "
                "the menu at the bottom for more."
            ),
        )
        embed.add_field(
            name="Dice Rolls",
            value=(
                "```/roll pool:POOL hunger:HUNGER difficulty:DIFFICULTY```"
                "For `HUNGER`, select `Use Current (or 0 for Mortals)` if using a "
                "character in the bot; otherwise select a number.\n"
                "**Example:** `/roll pool:5 hunger:2 difficulty:3`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Rolling with Traits",
            value=(
                "Roll with Trait names (requires character).\n"
                "**Example:** `/roll pool:manipulation+subterfuge "
                "hunger:Use Current (or 0 for Mortals) difficulty:3`\n\n"
                "Create a character with `/character wizard`."
            ),
            inline=False,
        )
        embed.add_field(
            name="Impairment",
            value=(
                "Impaired characters automatically lose 2 dice on affected rolls. If "
                "a power or rule negates it, use `impairment_category:Ignore`. To subtract it "
                "yourself instead, turn it off in `/settings` `scope:Yourself`."
            ),
            inline=False,
        )
        embed.add_field(
            name="Create a Character",
            value="`/character wizard`\nYou can use your character's Traits in rolls.",
            inline=False,
        )
        embed.add_field(
            name="Display Character",
            value="`/character display`",
            inline=False,
        )
        embed.add_field(name="Add Traits", value="`/traits add`")
        embed.add_field(name="Add Specialties", value="`/specialties add`")
        embed.add_field(
            name="Common Commands",
            value=(
                "The following commands are commonly used:\n\n"
                "`/rouse` — Perform a Rouse Check. Increases Hunger on failure\n"
                "`/slake` — Reduce Hunger\n"
                "`/awaken` — Perform a Rouse Check and heal Superficial Willpower damage\n"
                "`/bol` — Rouse for Blush of Life, taking Humanity into account\n"
                "`/mend` — Mend Superficial Health damage based on BP, performing a Rouse Check\n"
                "`/aggheal` — Perform three Rouse Checks to mend one Aggravated Health damage\n"
                "`/stain` — Add or remove Stains\n"
                "`/remorse` — Run a Remorse Check based on your current Stains"
            ),
            inline=False,
        )
        return embed

    def cog_page(self, cog: discord.Cog) -> discord.Embed:
        """A help page generated from a cog's description and commands."""
        entries = []
        for command in _slash_commands(cog):
            mention = self.bot.cmd_mention(command.qualified_name) or f"`/{command.qualified_name}`"
            entries.append(f"* {mention}: {command.description}")

        embed = self._base_embed(
            title=cog.qualified_name,
            description=f"{cog.description}\n\n" + "\n".join(entries),
        )

        apps = []
        context_commands = _context_commands(cog)
        for is_user, label in ((True, "member"), (False, "message")):
            if names := sorted(
                c.name for c in context_commands if isinstance(c, UserCommand) == is_user
            ):
                apps.append(f"**Right-click a {label}:** " + ", ".join(names))
        if apps:
            embed.add_field(name="Apps", value="\n".join(apps), inline=False)

        embed.set_footer(text="Click a command to paste it in your chat box.")
        return embed

    def _base_embed(self, *, title: str, description: str) -> discord.Embed:
        """Create an empty help embed."""
        embed = discord.Embed(title=title, description=description)
        embed.set_author(name=self.bot.me.display_name)
        embed.set_thumbnail(url=self.bot.me.display_avatar.url)
        return embed


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(Help(bot))
