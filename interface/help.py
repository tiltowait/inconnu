"""interface/help.py - Help commands"""

import discord
from discord.commands import SlashCommandGroup, slash_command
from discord.ext import commands
from discord.ui import Button, View

import inconnu
from inconnu.constants import PATREON, SUPPORT_URL


class _HelpView(View):
    """A view that has support buttons as well as command help buttons."""

    def __init__(self, *buttons, show_support=False):
        super().__init__(timeout=None)

        for button in buttons:
            self.add_item(button)

        if show_support:
            self.add_item(
                Button(label="New? Click here!", url="https://www.inconnu.app/#/quickstart", row=1)
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

            macros = Button(
                label="Macro Management",
                style=discord.ButtonStyle.primary,
                custom_id="persistent-macro",
            )
            macros.callback = self.show_macros_help

            self.overview_view = _HelpView(character, traits, macros, show_support=True)

        # Add the persistent views to the bot if we haven't already
        if not self.bot.persistent_views_added:
            self.bot.add_view(self.info_view)
            self.bot.add_view(self.overview_view)
            self.bot.persistent_views_added = True

    # Help Commands

    help_commands = SlashCommandGroup("help", "Help commands.")

    @help_commands.command(name="overview")
    async def help_overview(self, ctx):
        """Basic usage instructions."""
        await self.show_basic_help(ctx, False)

    @help_commands.command(name="traits")
    @commands.guild_only()
    async def help_traits(self, ctx):
        """Trait management instructions."""
        await self.show_traits_help(ctx, False)

    @help_commands.command(name="macros")
    @commands.guild_only()
    async def help_macros(self, ctx):
        """Macro usage instructions."""
        await self.show_macros_help(ctx, False)

    @help_commands.command(name="characters")
    @commands.guild_only()
    async def help_character_updates(self, ctx):
        """Display the valid character update keys."""
        await inconnu.character.update_help(ctx, ephemeral=False)

    @slash_command()
    async def info(self, ctx):
        """Display bot info."""
        embed = discord.Embed(
            title="Bot Information",
            description="**Inconnu** is a dice roller for Vampire: The Masquerade 5th Edition.",
        )
        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_thumbnail(url="https://www.inconnu.app/images/darkpack_logo2.webp")

        help_commands = [
            "`/help overview` - Basic help",
            "`/help characters` - Character updates help",
            "`/help traits` - Trait management help",
            "`/help macros` - Macro creation/editing help",
        ]

        embed.add_field(name="Help Commands", value="\n".join(help_commands), inline=False)
        embed.add_field(
            name="Framework", value="[Pycord 2.0](https://pycord.dev) using Python 3.10"
        )
        embed.add_field(
            name="Additional Packages",
            value="motor 3.0.0\nstatcord.py 3.1.0",
        )
        embed.add_field(name="Author", value="@tiltowait#8282", inline=False)

        embed.set_footer(
            text="Portions of the materials are the copyrights and trademarks of Paradox Interactive AB, and are used with permission. All rights reserved. For more information please visit worldofdarkness.com."
        )

        await inconnu.respond(ctx)(embed=embed, view=self.info_view)

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
            name="Roll",
            value=(
                "`/vr syntax:POOL HUNGER DIFFICULTY`\n\n"
                "Your `POOL` can be numbers or words. `HUNGER` can be a number 0-5 *or* "
                "the word `hunger`, which will use your character's current Hunger rating. "
                "`DIFFICULTY` can be any number 0 or higer. Defaults to 0 if omitted.\n\n"
                "You need to create a character to use traits. "
                "If you only supply `POOL`, then `HUNGER` and `DIFFICULTY` will both be 0.\n\n"
                "**Example:** `/vr syntax:manip+sub hunger 3` will roll Manipulation + "
                "Subterfuge, using current Hunger, at Difficulty 3."
            ),
            inline=False,
        )
        embed.add_field(
            name="Simplified roll syntax",
            value=(
                "`/roll pool:POOL hunger:HUNGER difficulty:DIFFICULTY`\n\n"
                "The same as `/vr`, only easier for new users. All parameters required."
            ),
            inline=False,
        )
        char_info = "`/character create`\nYou can use character attributes in rolls."
        embed.add_field(name="Create a character", value=char_info, inline=False)
        embed.add_field(name="Display character", value="`/character display`", inline=False)
        embed.add_field(name="Add traits", value="`/traits add`")
        embed.add_field(name="Add specialties", value="`/specialties add`")
        embed.add_field(
            name="Common commands",
            value=(
                "The following commands are commonly used:\n\n"
                "`/rouse` — Perform a Rouse check, automatically increasing Hunger if failed\n"
                "`/slake` — Reduce Hunger"
                "`/awaken` — Perform a Rouse check (if a vampire) and heal Willpower\n"
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
                "Many commands have a character: parameter. If you only have one character, "
                "it is usually optional. In commands where it is required, Discord makes it "
                "obvious."
            )
        )

        await inconnu.respond(ctx)(embed=embed, view=self.overview_view, ephemeral=ephemeral)

    async def show_traits_help(self, ctx, ephemeral=True):
        """Run the /traits help command."""
        embed = discord.Embed(
            title="Traits Management",
            description="This command group allows you to add, remove, or update character traits.",
        )
        embed.set_author(name=self.bot.user.display_name)
        embed.set_thumbnail(url=self.bot.user.avatar)
        embed.set_footer(text="Traits may be used in rolls. See /help overview for more info.")

        embed.add_field(
            name="Addition",
            value="`/traits add`\n**Example:** `/traits add traits:Oblivion=3 Chemistry=1`",
            inline=False,
        )

        embed.add_field(
            name="Deletion",
            value="`/traits delete`\n**Example:** `/traits delete traits:Oblivion`",
            inline=False,
        )

        embed.add_field(
            name="Modification",
            value="`/traits update`\n**Example:** `/traits update traits:Oblivion=2`",
            inline=False,
        )

        embed.add_field(
            name="Specialties",
            value="`/specialties add`\n**Example:** `/specialties add specialties:Grappling`",
            inline=False,
        )

        buttons = [
            Button(label="Documentation", url="https://www.inconnu.app/#/trait-management"),
            Button(label="Support", url=SUPPORT_URL),
        ]
        view = _HelpView(*buttons)

        await inconnu.respond(ctx)(embed=embed, view=view, ephemeral=ephemeral)

    async def show_macros_help(self, ctx, ephemeral=True):
        """Run the /macro help command."""
        embed = discord.Embed(
            title="Macros",
            description="This command group lets you define, delete, or update macros.",
        )
        embed.set_author(name=self.bot.user.display_name)
        embed.set_thumbnail(url=self.bot.user.avatar)
        embed.set_footer(text="Roll a macro with the /vm command!")

        embed.add_field(
            name="Creation", value="`/macro create`\nFill out the parameters offered.", inline=False
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
            Button(label="Documentation", url="https://www.inconnu.app/#/macros"),
            Button(label="Support", url=SUPPORT_URL),
        ]
        view = _HelpView(*buttons)

        await inconnu.respond(ctx)(embed=embed, view=view, ephemeral=ephemeral)

    async def show_character_help(self, ctx, ephemeral=True):
        """Run the /macro help command."""
        await inconnu.character.update_help(ctx, ephemeral=ephemeral)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(Help(bot))
