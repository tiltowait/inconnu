"""interface/help.py - Help commands"""

import discord
from discord.ext import commands
from discord_ui import ext
from discord_ui.cogs import slash_command, subslash_command
from discord_ui.components import LinkButton

from inconnu.constants import SUPPORT_URL

from . import debug


class Help(commands.Cog, name="Help"):
    """A class for housing the /help command."""

    def __init__(self, bot):
        self.bot = bot

        help_button = LinkButton("https://www.inconnu-bot.com/#/quickstart", "New? Click here!")
        support_button = LinkButton(SUPPORT_URL, "Support")
        patreon_button = LinkButton("https://www.patreon.com/tiltowait", "Patreon")

        self.buttons = [help_button, support_button, patreon_button]


    @slash_command("help", description="Help with basic functions.")
    async def help_command(self, ctx):
        """Basic usage instructions."""
        embed = discord.Embed(
            title="Inconnu Help",
            description="Basic commands listing. Click the link for detailed documentation."
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)

        embed.add_field(name="Roll", value="`/vr pool hunger difficulty`", inline=False)
        char_info = "`/character create`\nYou can use character attributes in rolls."
        embed.add_field(name="Create a character", value=char_info, inline=False)
        embed.add_field(name="Display character", value="`/character display`", inline=False)
        embed.add_field(name="Add traits", value="`/traits add`")

        await ctx.respond(embed=embed, components=self.buttons)


    @ext.check_failed("Traits require characters and aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_command(
        base_names="traits",
        name="help",
        guild_ids=debug.WHITELIST
    )
    async def help(self, ctx):
        """Trait management instructions."""
        embed = discord.Embed(
            title="Traits Management",
            description="This command group allows you to add, remove, or update character traits."
        )
        embed.set_author(name=ctx.bot.user.display_name, icon_url=ctx.bot.user.avatar)
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
            LinkButton("https://www.inconnu-bot.com/#/trait-management", "Documentation"),
            LinkButton(SUPPORT_URL, "Support")
        ]

        await ctx.respond(embed=embed, components=buttons)


    @ext.check_failed("Macros require characters and aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_command(
        base_names="macro",
        name="help",
        guild_ids=debug.WHITELIST
    )
    async def macro_help(self, ctx):
        """Macro usage instructions."""
        embed = discord.Embed(
            title="Macros",
            description="This command group lets you define, delete, or update macros."
        )
        embed.set_author(name=ctx.bot.user.display_name, icon_url=ctx.bot.user.avatar)
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
            LinkButton("https://www.inconnu-bot.com/#/macros", "Documentation"),
            LinkButton(SUPPORT_URL, "Support")
        ]

        await ctx.respond(embed=embed, components=buttons)


    @slash_command(guild_ids=debug.WHITELIST)
    async def info(self, ctx):
        """Display bot info."""
        embed = discord.Embed(
            title="Bot Information",
            description="A dice roller for Vampire: The Masquerade 5th Edition."
        )
        embed.set_author(name=ctx.bot.user.display_name, icon_url=ctx.bot.user.avatar)
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

        await ctx.respond(embed=embed, components=self.buttons)
