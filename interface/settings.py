"""interface/settings.py - Settings-related commands."""

import discord

from discord.ext import commands
from discord_ui import SlashOption
from discord_ui.cogs import slash_command

import inconnu
from . import debug


class SettingsCommands(commands.Cog):
    """Settings-related commands."""

    @slash_command(
        options=[
            SlashOption(int, "enable",
                choices=[
                    ("Yes", 1),
                    ("No", 0)
                ],
                required=True
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def accessibility(self, ctx, enable):
        """Enable or disable accessibility mode for yourself."""
        enable = bool(enable)
        response = inconnu.settings.set_accessibility(ctx, enable, "user")

        await ctx.respond(response)


    @slash_command(
        name="set",
        options=[
            SlashOption(int, "oblivion_stains",
                description="Which Rouse results should give Oblivion stain warnings",
                choices=[
                    ("1s and 10s (RAW)", 100),
                    ("1s only", 1),
                    ("10s only", 10),
                    ("Never", 0)
                ]
            ),
            SlashOption(int, "accessibility",
                description="Whether to enable or disable accessibility",
                choices=[
                    ("Yes", 1),
                    ("No", 0)
                ]
            ),
        ],
        guild_ids=debug.WHITELIST
    )
    async def set(self, ctx, oblivion_stains=None, accessibility=None):
        """(Admin-only) Assign server-wide settings."""
        try:
            responses = []

            if oblivion_stains is not None:
                response = inconnu.settings.set_oblivion_stains(ctx, oblivion_stains)
                responses.append(response)

            if accessibility is not None:
                accessibility = bool(accessibility)
                response = inconnu.settings.set_accessibility(ctx, accessibility, "guild")
                responses.append(response)

            if len(responses) > 0:
                await ctx.respond("\n".join(responses))
            else:
                await self.settings(ctx)

        except PermissionError as err:
            await ctx.respond(err, hidden=True)


    @slash_command(
        name="settings",
        guild_ids=debug.WHITELIST
    )
    async def settings(self, ctx):
        """Display the settings in effect."""
        accessibility = "ON" if inconnu.settings.accessible(ctx.author) else "OFF"
        oblivion_stains = inconnu.settings.oblivion_stains(ctx.guild)
        oblivion_stains = map(lambda s: f"`{s}`", oblivion_stains)

        msg = f"Accessibility mode: `{accessibility}`"
        msg += "\nOblivion Rouse stains: " + " or ".join(oblivion_stains)

        embed = discord.Embed(
            title="Server Settings",
            description=msg
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon or "")
        embed.set_footer(text="Modify settings with /set")

        await ctx.respond(embed=embed)
