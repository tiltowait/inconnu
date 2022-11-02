"""Roleplay commands."""
# pylint: disable=no-self-use

import discord
from discord.commands import Option, slash_command
from discord.ext import commands

import inconnu


class RoleplayCog(commands.Cog):
    """A cog with roleplay commands."""

    def __init__(self, bot):
        self.bot = bot

    @slash_command()
    async def post(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character to post as", required=True),
        mention: Option(discord.Member, "The player to mention", required=False),
    ):
        """Make an RP post as your character. Uses your current header."""
        await inconnu.roleplay.post(ctx, character, mention=mention)

    @slash_command()
    async def search(
        self,
        ctx: discord.ApplicationContext,
        user: Option(discord.Member, "The user who made the post"),
        content: Option(str, "What to search for"),
    ):
        """Search for an RP post. Displays up to 5 results."""
        await inconnu.roleplay.search(ctx, user, content)


def setup(bot):
    """Set up the cog."""
    bot.add_cog(RoleplayCog(bot))