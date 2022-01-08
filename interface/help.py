"""interface/help.py - Help commands"""

import discord
from discord.ext import commands
from discord_ui.cogs import slash_command
from discord_ui.components import LinkButton


class Help(commands.Cog, name="Help"):
    """A class for housing the /help command."""

    @slash_command("help", description="Help with basic functions.")
    async def help_command(self, ctx):
        """Display a help message."""
        embed = discord.Embed(
            title="Inconnu Help",
            description="Basic commands listing. Click the link for detailed documentation."
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)

        embed.add_field(name="Roll", value="`/vr pool hunger difficulty`", inline=False)
        char_info = "`/character create`\nIf you have a character, you can use their traits in rolls."
        embed.add_field(name="Create a character", value=char_info, inline=False)
        embed.add_field(name="Display character", value="`/character display`", inline=False)
        embed.add_field(name="Add traits", value="`/traits add`")

        help_button = LinkButton(
            "https://www.inconnu-bot.com/#/quickstart",
            label="New? Read the Quickstart!"
        )
        patreon_button = LinkButton(
            "https://www.patreon.com/tiltowait",
            label="Patreon"
        )

        await ctx.respond(embed=embed, components=[help_button, patreon_button])
