"""interface/help.py - Help commands"""

import discord
from discord.commands import SlashCommandGroup, slash_command
from discord.ext import commands
from discord.ui import Button, View

import inconnu
from inconnu.constants import SUPPORT_URL


class _HelpView(View):
    """A view that has support buttons as well as command help buttons."""

    def __init__(self, *buttons, show_support=False):
        super().__init__()

        for button in buttons:
            self.add_item(button)

        if show_support:
            self.add_item(Button(
                label="New? Click here!",
                url="https://www.inconnu-bot.com/#/quickstart",
                row=1
            ))
            self.add_item(Button(label="Support", url=SUPPORT_URL, row=1))
            self.add_item(Button(label="Patreon", url="https://www.patreon.com/tiltowait", row=1))


class Help(commands.Cog):
    """A class for housing the /help command."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot


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
            description="A dice roller for Vampire: The Masquerade 5th Edition."
        )
        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_thumbnail(url="https://www.inconnu-bot.com/images/darkpack_logo2.webp")

        help_commands = [
            "`/help` - Basic help",
            "`/character help` - Character updates help",
            "`/traits help` - Trait management help",
            "`/macro help` - Macro creation/editing help"
        ]

        embed.add_field(name="Help Commands", value="\n".join(help_commands), inline=False)
        embed.add_field(
            name="Frameworks",
            value="discord.py 2.0 alpha\ndiscord-ui 5.2.0",
            inline=False
        )
        embed.add_field(name="Author", value="@tiltowait#8282", inline=False)

        embed.set_footer(
            text="Portions of the materials are the copyrights and trademarks of Paradox Interactive AB, and are used with permission. All rights reserved. For more information please visit worldofdarkness.com."
        )

        help_button = Button(label="Help", style=discord.ButtonStyle.primary, row=0)
        help_button.callback = self.show_basic_help

        view = _HelpView(help_button, show_support=True)

        await self._send(ctx, embed=embed, view=view)


    # Callbacks

    async def show_basic_help(self, ctx, ephemeral=True):
        """Run the /traits help command."""
        embed = discord.Embed(
            title="Inconnu Help",
            description="Basic commands listing. Click the link for detailed documentation."
        )
        embed.set_author(name=ctx.user.display_name, icon_url=ctx.user.display_avatar)

        embed.add_field(name="Roll", value="`/vr syntax:pool hunger difficulty`", inline=False)
        char_info = "`/character create`\nYou can use character attributes in rolls."
        embed.add_field(name="Create a character", value=char_info, inline=False)
        embed.add_field(name="Display character", value="`/character display`", inline=False)
        embed.add_field(name="Add traits", value="`/traits add`")

        character = Button(label="Character Updater", style=discord.ButtonStyle.primary, row=0)
        character.callback = self.show_character_help

        traits = Button(label="Traits Management", style=discord.ButtonStyle.primary, row=0)
        traits.callback = self.show_traits_help

        macros = Button(label="Macro Management", style=discord.ButtonStyle.primary, row=0)
        macros.callback = self.show_macros_help

        view = _HelpView(character, traits, macros, show_support=True)

        await self._send(ctx, embed=embed, view=view, ephemeral=ephemeral)


    async def show_traits_help(self, ctx, ephemeral=True):
        """Run the /traits help command."""
        embed = discord.Embed(
            title="Traits Management",
            description="This command group allows you to add, remove, or update character traits."
        )
        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_footer(text="Traits may be used in rolls. See /help for more info.")

        embed.add_field(
            name="Creation",
            value="`/traits add`\n**Example:** `/traits add traits:Oblivion=3 Auspex=2`",
            inline=False
        )

        embed.add_field(
            name="Deletion",
            value="`/traits delete`\n**Example:** `/traits delete traits:Oblivion`",
            inline=False
        )

        embed.add_field(
            name="Modification",
            value="`/traits update`\n**Example:** `/traits update traits:Oblivion=2`",
            inline=False
        )

        buttons = [
            Button(label="Documentation", url="https://www.inconnu-bot.com/#/trait-management", row=0),
            Button(label="Support", url=SUPPORT_URL, row=0)
        ]
        view = _HelpView(*buttons)

        await self._send(ctx, embed=embed, view=view, ephemeral=ephemeral)


    async def show_macros_help(self, ctx, ephemeral=True):
        """Run the /macro help command."""
        embed = discord.Embed(
            title="Macros",
            description="This command group lets you define, delete, or update macros."
        )
        embed.set_author(name=self.bot.user.display_name, icon_url=self.bot.user.avatar)
        embed.set_footer(text="Roll a macro with the /vm command!")

        embed.add_field(
            name="Creation",
            value="`/macro create`\nFill out the parameters offered.",
            inline=False
        )
        embed.add_field(
            name="Deletion",
            value="`/macro delete`\nSpecify a macro name. This is non-reversible!",
            inline=False
        )
        embed.add_field(
            name="Modification",
            value="`/macro update`\n**Example:** `/macro update macro:hunt parameters:pool=...`",
            inline=False
        )

        buttons = [
            Button(label="Documentation", url="https://www.inconnu-bot.com/#/macros", row=0),
            Button(label="Support", url=SUPPORT_URL, row=0)
        ]
        view = _HelpView(*buttons)

        await self._send(ctx, embed=embed, view=view, ephemeral=ephemeral)


    async def show_character_help(self, ctx, ephemeral=True):
        """Run the /macro help command."""
        await inconnu.character.update_help(ctx, ephemeral=ephemeral)


    async def _send(self, ctx, **message_content):
        """Send the message content. Wrapper that checks for context type."""
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(**message_content)
            else:
                await ctx.response.send_message(**message_content)
        else:
            await ctx.respond(**message_content)



def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(Help(bot))
