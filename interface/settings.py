"""interface/settings.py - Settings-related commands."""

import discord

from discord.ext import commands
from discord_ui import SlashOption
from discord_ui.cogs import slash_command

import inconnu
from . import debug


async def _available_scopes(_, ctx):
    """Determine the available settings scopes."""
    if ctx.author.guild_permissions.administrator:
        return [("Self only", "user"), ("Entire server", "guild")]
    return [("Self only", "user")]


async def _available_oblivion_options(_, ctx):
    """Determine the available Oblivion stains options."""
    if ctx.author.guild_permissions.administrator:
        return [
            ("1s and 10s (RAW)", "100"),
            ("1s only", "1"),
            ("10s only", "10"),
            ("None", "0")
        ]
    return []


class SettingsCommands(commands.Cog):
    """Settings-related commands."""

    @slash_command(
        name="set",
        options=[
            SlashOption(str, "oblivion_stains",
                description="(Admin) Which Rouse results should give stain warnings",
                autocomplete=True, choice_generator=_available_oblivion_options
            ),
            SlashOption(int, "accessibility",
                description="Whether to enable or disable accessibility",
                choices=[
                    ("Yes", 1),
                    ("No", 0)
                ]
            ),
            SlashOption(str, "scope",
                description="Set for yourself or the entire server",
                autocomplete=True, choice_generator=_available_scopes
            ),
        ],
        guild_ids=debug.WHITELIST
    )
    async def set(self, ctx, oblivion_stains=None, accessibility=None, scope="user"):
        """Assign various user- or server-wide settings."""
        try:
            responses = []

            if oblivion_stains is not None:
                response = inconnu.settings.set_oblivion_stains(ctx, oblivion_stains)
                responses.append(response)

            if accessibility is not None:
                accessibility = bool(accessibility)
                response = inconnu.settings.set_accessibility(ctx, accessibility, scope)
                responses.append(response)

            if len(responses) > 0:
                await ctx.respond("\n".join(responses))
            else:
                await ctx.respond("No settings supplied!", hidden=True)

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
