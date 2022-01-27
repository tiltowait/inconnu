"""interface/settings.py - Settings-related commands."""

import discord
from discord.commands import Option, OptionChoice, slash_command
from discord.ext import commands

import inconnu


class SettingsCommands(commands.Cog):
    """Settings-related commands."""

    @slash_command()
    @commands.guild_only()
    async def accessibility(
        self,
        ctx: discord.ApplicationContext,
        enable: Option(int, "Enable accessibility mode for yourself",
            choices=[
                OptionChoice("Yes", 1),
                OptionChoice("No", 0)
            ]
        )
    ):
        """Enable or disable accessibility mode for yourself."""
        enable = bool(enable)
        response = inconnu.settings.set_accessibility(ctx, enable, "user")

        await ctx.respond(response)


    @slash_command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set(
        self,
        ctx: discord.ApplicationContext,
        oblivion_stains: Option(int, "Which Rouse results should give Oblivion stain warnings",
            choices=[
                OptionChoice("1s and 10s (RAW)", 100),
                OptionChoice("1s only", 1),
                OptionChoice("10s only", 10),
                OptionChoice("Never", 0)
            ]
        ),
        accessibility: Option(int, "Whether to enable or disable accessibility",
            choices=[
                OptionChoice("Yes", 1),
                OptionChoice("No", 0)
            ]
        )
    ):
        """(Admin-only) Assign server-wide settings."""
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


    @slash_command()
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
