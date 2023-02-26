"""interface/help.py - Help commands"""
# TODO: Migrate to _empty_embed

from enum import Enum

import discord
from discord import option
from discord.commands import slash_command
from discord.ext import commands
from discord.ui import Button, View

import inconnu
from config import web_asset
from inconnu.constants import PATREON, SUPPORT_URL


class Section(str, Enum):
    """Represents a help section."""

    OVERVIEW = "Overview"
    CHARACTERS = "Characters"
    TRAITS = "Traits"
    DISCIPLINES = "Disciplines"
    SPECIALTIES = "Specialties"
    MACROS = "Macros"

    @classmethod
    def all(cls) -> list[str]:
        """A list of all values."""
        return [section.value for section in cls]


class _HelpView(View):
    """A view that has support buttons as well as command help buttons."""

    def __init__(self, *buttons, show_support=False):
        super().__init__(timeout=None)

        for button in buttons:
            self.add_item(button)

        if show_support:
            self.add_item(
                Button(
                    label="New? Click here!",
                    url="https://docs.inconnu.app/guides/quickstart",
                    row=1,
                )
            )
            self.add_item(Button(label="Support", url=SUPPORT_URL, row=1))
            self.add_item(Button(label="Patreon", url=PATREON, row=1))


class Help(commands.Cog):
    """A class for housing the /help command."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.info_view = None
        self.overview_view = None

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        """Attach the persistent view."""

        # Create the persistent views if we haven't already
        if self.info_view is None:
            help_button = Button(
                label="Help",
                style=discord.ButtonStyle.primary,
                custom_id="persistent-info",
            )
            help_button.callback = self.show_basic_help

            self.info_view = _HelpView(help_button, show_support=True)

        if self.overview_view is None:
            character = Button(
                label="Character Updater",
                style=discord.ButtonStyle.primary,
                custom_id="persistent-character",
            )
            character.callback = self.show_character_help

            traits = Button(
                label="Traits Management",
                style=discord.ButtonStyle.primary,
                custom_id="persistent-traits",
            )
            traits.callback = self.show_traits_help

            disciplines = Button(
                label="Disciplines",
                style=discord.ButtonStyle.primary,
                custom_id="persistent-disciplines",
            )
            disciplines.callback = self.show_disciplines_help

            specialties = Button(
                label="Specialties",
                style=discord.ButtonStyle.primary,
                custom_id="persistent-specialties",
            )
            specialties.callback = self.show_specialties_help

            macros = Button(
                label="Macros",
                style=discord.ButtonStyle.primary,
                custom_id="persistent-macro",
            )
            macros.callback = self.show_macros_help

            self.overview_view = _HelpView(
                character, traits, disciplines, specialties, macros, show_support=True
            )

        # Add the persistent views to the bot if we haven't already
        if not self.bot.persistent_views_added:
            self.bot.add_view(self.info_view)
            self.bot.add_view(self.overview_view)
            self.bot.persistent_views_added = True

    # Help Commands

    @slash_command(name="help")
    @option("section", description="The help section to look up", choices=Section.all())
    async def help_command(self, ctx: discord.ApplicationContext, section: str):
        """View help on a particular section."""
        match section:
            case Section.OVERVIEW:
                await self.show_basic_help(ctx, False)
            case Section.CHARACTERS:
                await inconnu.character.update_help(ctx, ephemeral=False)
            case Section.TRAITS:
                await self.show_traits_help(ctx, False)
            case Section.DISCIPLINES:
                await self.show_disciplines_help(ctx, False)
            case Section.SPECIALTIES:
                await self.show_specialties_help(ctx, False)
            case Section.MACROS:
                await self.show_macros_help(ctx, False)
            case _:
                raise NotImplementedError("Oops")

    @slash_command()
    async def info(self, ctx):
        """Display bot info."""
        embed = discord.Embed(
            title="Bot Information",
            description="**Inconnu** is a dice roller for Vampire: The Masquerade 5th Edition.",
        )
        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_thumbnail(url=web_asset("darkpack_logo2.webp"))

        embed.add_field(
            name="Framework", value="[Pycord 2.3](https://pycord.dev) using Python 3.10"
        )
        embed.add_field(
            name="Additional Packages",
            value="motor 3.0.0\nstatcord.py 3.1.0",
        )
        embed.add_field(name="Author", value="@tiltowait#8282", inline=False)

        embed.set_footer(
            text=(
                "Portions of the materials are the copyrights and trademarks "
                "of Paradox Interactive AB, and are used with permission. All "
                "rights reserved. For more information please visit "
                "worldofdarkness.com."
            )
        )

        await inconnu.utils.cmd_replace(ctx, embed=embed, view=self.info_view)

    # Callbacks

    async def show_basic_help(self, ctx, ephemeral=True):
        """Run the /traits help command."""
        embed = discord.Embed(
            title="Commands Help",
            description=(
                "Basic commands listing. Click the links for detailed documentation!"
                " Items such as `pool:` or `hunger:` are Discord command parameters."
                " They don't need to be typed, as Discord adds them automatically."
                "\n\nA word in `CAPS` indicates where you enter your input. For,"
                " instance, `hunger:HUNGER` would look like `hunger:3` in the Discord"
                " interface after selecting 3 Hunger."
            ),
        )
        embed.set_author(name=self.bot.user.display_name)
        embed.set_thumbnail(url=self.bot.user.avatar)

        embed.add_field(
            name="Dice Rolls",
            value=(
                "`/roll pool:POOL hunger:HUNGER difficulty:DIFFICULTY`\n\n"
                "Your `POOL` can be numbers or words. For `HUNGER`, select `Current Hunger`"
                "if using a character in the bot; otherwise select a number. "
                "`DIFFICULTY` can be any number 0 or higer. Defaults to 0 if omitted.\n\n"
                "You must create a character to use traits.\n\n"
                "**Example:** `/roll pool:manip+sub hunger:Current Hunger difficulty:3` "
                "will roll Manipulation + Subterfuge, using current Hunger, at Difficulty 3."
            ),
            inline=False,
        )
        embed.add_field(
            name="Alternate roll syntax",
            value=(
                "`/vr` - Combines roll elements into one line, similar to Thirst. Use "
                "`hunger` to use your character's current Hunger, or give a number.\n"
                "**Example:** `/vr syntax:manip+sub hunger 3`"
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

        await inconnu.utils.cmd_replace(
            ctx, embed=embed, view=self.overview_view, ephemeral=ephemeral
        )

    async def show_traits_help(self, ctx, ephemeral=True):
        """Run the /traits help command."""
        embed = discord.Embed(
            title="Traits Management",
            description="This command group allows you to add, remove, or update character traits.",
        )
        embed.set_author(name=self.bot.user.display_name)
        embed.set_thumbnail(url=self.bot.user.avatar)

        embed.add_field(
            name="Add custom traits",
            value="`/traits add`\n**Example:** `/traits add traits:Forgery=1 Stunning=2`",
            inline=False,
        )
        embed.add_field(
            name="Delete custom traits",
            value="`/traits delete`\n**Example:** `/traits delete traits:Forgery`",
            inline=False,
        )
        embed.add_field(
            name="Modify traits",
            value="`/traits update`\n**Example:** `/traits update traits:Strength=2 Brawl=3`",
            inline=False,
        )
        embed.add_field(
            name="Disciplines, Specialties, & Powers",
            value="See the respective sections of this help command.",
            inline=False,
        )
        embed.add_field(name="List traits", value="`/traits list`", inline=False)
        embed.add_field(
            name="Roll with a trait",
            value="**Example:** `/roll pool:Strength + Brawl hunger:Current Hunger difficulty:1`",
            inline=False,
        )

        buttons = [
            Button(label="Documentation", url="https://docs.inconnu.app/command-reference/traits"),
            Button(label="Support", url=SUPPORT_URL),
        ]
        view = _HelpView(*buttons)

        await inconnu.utils.cmd_replace(ctx, embed=embed, view=view, ephemeral=ephemeral)

    async def show_specialties_help(self, ctx, ephemeral=True):
        """Show help for using/adding/removing specialties."""
        embed = self._empty_embed(
            title="Specialties",
            description="With these commands, you may add or remove skill specialties.",
        )
        embed.add_field(
            name="Add specialties",
            value=(
                "`/specialties add` - Add specialties to standard or custom skills.\n"
                "**Example:** `/specialties add specialties:Performance=Piano,Singing Craft=Ammo`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Remove specialties",
            value=(
                "`/specialties remove` - Remove specialties from standard or custom skills.\n"
                "**Example:** `/specialties remove specialties:Brawl=Kindred`"
            ),
            inline=False,
        )
        embed.add_field(name="List specialties", value="`/traits list`")
        embed.add_field(
            name="Roll specialty",
            value=(
                "**Example:** "
                "`/roll pool:Strength + Brawl.Kindred hunger:Current Hunger difficulty:1`"
            ),
            inline=False,
        )
        embed.set_footer(text="You may add and remove multiple specialties at a time.")

        buttons = [
            Button(
                label="Documentation",
                url="https://docs.inconnu.app/guides/quickstart/specialties",
            ),
            Button(label="Support", url=SUPPORT_URL),
        ]
        view = _HelpView(*buttons)

        await inconnu.utils.cmd_replace(ctx, embed=embed, view=view, ephemeral=ephemeral)

    async def show_disciplines_help(self, ctx, ephemeral=True):
        """Show help for using/adding/removing specialties."""
        embed = self._empty_embed(
            title="Disciplines & Powers",
            description="With these commands, you may add or remove Disciplines and powers.",
        )
        embed.add_field(
            name="Add Disciplines",
            value=(
                "`/disciplines add` - Add one or more Disciplines and their ratings.\n"
                "**Example:** `/disciplines add:Auspex=2 Oblivion=3`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Remove Disciplines",
            value=(
                "`/disciplines remove` - Remove one or more Disciplines.\n"
                "**Example:** `/disciplines remove:Oblivion Auspex`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Add Powers",
            value=(
                "`/powers add` - Add one or more powers to Disciplines.\n"
                "**Example:** `/powers add powers:Potence=Prowess,SoaringLeap`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Remove Powers",
            value=(
                "`/powers remove` - Remove one or more powers to Disciplines.\n"
                "**Example:** `/powers remove powers:Potence=Prowess Auspex=Telepathy`"
            ),
            inline=False,
        )
        embed.add_field(name="List Disciplines & Powers", value="`/traits list`")
        embed.add_field(
            name="Roll Discipline with Power",
            value=(
                "**Example:** "
                "`/roll pool:Resolve + Auspex.Telepathy hunger:Current Hunger difficulty:3`"
            ),
            inline=False,
        )

        buttons = [
            Button(
                label="Documentation",
                url="https://docs.inconnu.app/guides/quickstart/disciplines-and-powers",
            ),
            Button(label="Support", url=SUPPORT_URL),
        ]
        view = _HelpView(*buttons)

        await inconnu.utils.cmd_replace(ctx, embed=embed, view=view, ephemeral=ephemeral)

    async def show_macros_help(self, ctx, ephemeral=True):
        """Run the /macro help command."""
        embed = discord.Embed(
            title="Macros",
            description="This command group lets you define, delete, or update macros.",
        )
        embed.set_author(name=self.bot.user.display_name)
        embed.set_thumbnail(url=self.bot.user.avatar)

        embed.add_field(
            name="Creation", value="`/macro create`\nFill out the parameters offered.", inline=False
        )
        embed.add_field(
            name="Use",
            value="`/vm`\n**Example:** `/vm syntax:hunt`. You may override Hunger and Difficulty.",
        )
        embed.add_field(
            name="Deletion",
            value="`/macro delete`\nSpecify a macro name. This is non-reversible!",
            inline=False,
        )
        embed.add_field(
            name="Modification",
            value="`/macro update`\n**Example:** `/macro update macro:hunt parameters:pool=...`",
            inline=False,
        )

        buttons = [
            Button(label="Documentation", url="https://docs.inconnu.app/command-reference/macros"),
            Button(label="Support", url=SUPPORT_URL),
        ]
        view = _HelpView(*buttons)

        await inconnu.utils.cmd_replace(ctx, embed=embed, view=view, ephemeral=ephemeral)

    async def show_character_help(self, ctx, ephemeral=True):
        """Run the /macro help command."""
        await inconnu.character.update_help(ctx, ephemeral=ephemeral)

    def _empty_embed(self, *, title: str, description: str):
        """Create an empty help embed."""
        embed = discord.Embed(title=title, description=description)
        embed.set_author(name=self.bot.user.display_name)
        embed.set_thumbnail(url=self.bot.user.avatar)

        return embed


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(Help(bot))
