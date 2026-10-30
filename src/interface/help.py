"""interface/help.py - Help commands"""

from typing import TYPE_CHECKING, cast

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
from utils import cmd_replace
from utils.cmdreplace import mention_embed_commands
from utils.urls import docs_url, web_asset

if TYPE_CHECKING:
    from bot import InconnuBot

HELP_MENU_ID = "help-menu"
OVERVIEW = "Overview"
OVERVIEW_DESCRIPTION = "Rolling basics and common commands."

# Cogs left out of the help menu, by qualified name
HIDDEN_COGS = frozenset({"AdminCog", "Help"})


def overview_page(bot: InconnuBot) -> discord.Embed:
    """The hand-written overview page."""
    embed = _base_embed(
        bot,
        title="Commands Help",
        description=(
            "Basic commands listing. Use the menu below to see every command!"
            " Items such as `pool:` or `hunger:` are Discord command parameters."
            " They don't need to be typed, as Discord adds them automatically."
            "\n\nA word in `CAPS` indicates where you enter your input. For,"
            " instance, `hunger:HUNGER` would look like `hunger:3` in the Discord"
            " interface after selecting 3 Hunger."
        ),
    )
    embed.add_field(
        name="Dice Rolls",
        value=(
            "`/roll pool:POOL hunger:HUNGER difficulty:DIFFICULTY`\n\n"
            "For `HUNGER`, select `Current Hunger` if using a character "
            "in the bot; otherwise select a number.\n"
            "**Example:** `/roll pool:5 hunger:2 difficulty:3`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Rolling with traits",
        value=(
            "If you have a character, you can roll with trait names.\n"
            "**Example:** `/roll pool:manipulation+subterfuge "
            "hunger:Current Hunger difficulty:3`\n\n"
            "Create a character with `/character create`."
        ),
        inline=False,
    )
    embed.add_field(
        name="Alternate roll syntax",
        value=(
            "`/vr` - Combines roll elements into one line, similar to Thirst. Type "
            "`hunger` to use your character's current Hunger, or give a number.\n"
            "**Example:** `/vr syntax:manip+sub hunger 3`"
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
        name="Hidden dice",
        value=(
            "Use `dice:Hide` to show others only the outcome and pool. You'll privately "
            "see the full roll and its buttons. Admins can restrict it in `/settings`."
        ),
        inline=False,
    )
    embed.add_field(
        name="Create a character",
        value="`/character create`\nYou can use character attributes in rolls.",
        inline=False,
    )
    embed.add_field(
        name="Display character",
        value="`/character display`",
        inline=False,
    )
    embed.add_field(name="Add traits", value="`/traits add`")
    embed.add_field(name="Add specialties", value="`/specialties add`")
    embed.add_field(
        name="Common commands",
        value=(
            "The following commands are commonly used:\n\n"
            "`/rouse` — Perform a Rouse check. Increases Hunger on failure\n"
            "`/slake` — Reduce Hunger\n"
            "`/awaken` — Perform a Rouse check and heal Willpower\n"
            "`/bol` — Rouse for Blush of Life, taking Humanity into account\n"
            "`/mend` — Mend Superficial Health damage based on BP, performing a Rouse check\n"
            "`/aggheal` — Perform three Rouse checks to mend one Aggravated Health damage\n"
            "`/stain` — Add or remove Stains\n"
            "`/remorse` — Run a Remorse check based on your current Stains"
        ),
        inline=False,
    )
    embed.set_footer(
        text=(
            "Many commands have a 'character' parameter, which is usually "
            "optional. When it's required, Discord makes it obvious."
        )
    )
    return embed


def help_cogs(bot: InconnuBot) -> dict[str, discord.Cog]:
    """The cogs with a help page, by name, in menu order."""
    return {
        name: cog
        for name, cog in sorted(bot.cogs.items())
        if name not in HIDDEN_COGS and (_slash_commands(cog) or _context_commands(cog))
    }


def help_sections(bot: InconnuBot) -> list[str]:
    """The help sections, in menu order."""
    return [OVERVIEW, *help_cogs(bot)]


def resolve_section(bot: InconnuBot, name: str) -> str:
    """The help section matching the name, ignoring case. Unknown names resolve
    to the overview."""
    folded = name.casefold()
    return next((s for s in help_sections(bot) if s.casefold() == folded), OVERVIEW)


def section_descriptions(bot: InconnuBot) -> dict[str, str]:
    """The help sections' menu subtitles, by section, in menu order."""
    return {
        OVERVIEW: OVERVIEW_DESCRIPTION,
        **{name: cog.description for name, cog in help_cogs(bot).items()},
    }


def cog_page(bot: InconnuBot, cog: discord.Cog) -> discord.Embed:
    """A help page generated from a cog's description and commands."""
    entries = []
    for command in _slash_commands(cog):
        mention = bot.cmd_mention(command.qualified_name) or f"`/{command.qualified_name}`"
        entries.append(f"* {mention}: {command.description}")

    embed = _base_embed(
        bot,
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


def help_page(bot: InconnuBot, section: str) -> discord.Embed:
    """The page for a help section. Unknown sections show the overview."""
    if cog := help_cogs(bot).get(section):
        embed = cog_page(bot, cog)
    else:
        embed = overview_page(bot)
    mention_embed_commands(bot, embed)
    return embed


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


async def _section_options(ctx: discord.AutocompleteContext) -> list[str]:
    """The help sections containing what the user has typed."""
    typed = (ctx.value or "").casefold()
    return [s for s in help_sections(cast("InconnuBot", ctx.bot)) if typed in s.casefold()]


def _base_embed(bot: InconnuBot, *, title: str, description: str) -> discord.Embed:
    """Create an empty help embed."""
    embed = discord.Embed(title=title, description=description)
    embed.set_author(name=bot.me.display_name)
    embed.set_thumbnail(url=bot.me.display_avatar.url)
    return embed


class HelpMenu(Select["HelpView"]):
    """The help section selector. Stateless, so it keeps working across restarts."""

    def __init__(self, sections: dict[str, str], selected: str):
        super().__init__(
            custom_id=HELP_MENU_ID,
            placeholder="Select help section",
            options=[
                discord.SelectOption(
                    label=section, description=description, default=section == selected
                )
                for section, description in sections.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        """Show the selected section."""
        bot = cast("InconnuBot", interaction.client)
        section = self.values[0] if self.values else OVERVIEW
        await interaction.response.edit_message(
            embed=help_page(bot, section), view=HelpView(bot, section)
        )


class HelpView(View):
    """The persistent help menu, plus support links."""

    def __init__(self, bot: InconnuBot, selected: str = OVERVIEW):
        super().__init__(timeout=None)
        self.add_item(HelpMenu(section_descriptions(bot), selected))
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
            self.bot.add_view(HelpView(self.bot))
            self.bot.persistent_views_added = True

    @slash_command(name="help")
    @option(
        "section",
        description="The help section to show",
        autocomplete=_section_options,
        default=OVERVIEW,
    )
    async def help_command(self, ctx: AppCtx, section: str):
        """See the bot's commands and how to use them."""
        section = resolve_section(self.bot, section)
        await ctx.respond(embed=help_page(self.bot, section), view=HelpView(self.bot, section))

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

        await cmd_replace(ctx, embed=embed, view=View(*support_buttons(), timeout=None))


def setup(bot: InconnuBot):
    """Add the cog to the bot."""
    bot.add_cog(Help(bot))
