"""interface/settings.py - Settings-related commands."""
# pylint: disable=no-self-use

import discord
from discord.commands import (Option, OptionChoice, SlashCommandGroup,
                              slash_command)
from discord.ext import commands

import inconnu


class SettingsCommands(commands.Cog):
    """Settings-related commands."""

    @slash_command()
    @commands.guild_only()
    async def accessibility(
        self,
        ctx: discord.ApplicationContext,
        enable: Option(
            int,
            "Enable accessibility mode for yourself",
            choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
        ),
    ):
        """Enable or disable accessibility mode for yourself."""
        enable = bool(enable)
        response = await inconnu.settings.set_accessibility(ctx, enable, "user")

        await ctx.respond(response)

    settings = SlashCommandGroup("settings", "Server settings commands.")

    @settings.command(name="set")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set(
        self,
        ctx: discord.ApplicationContext,
        experience_permissions: Option(
            str,
            "Whether users should be allowed to edit their XP totals.",
            choices=[
                OptionChoice("Unrestricted", "unrestricted"),
                OptionChoice("Unspent XP only", "unspent_only"),
                OptionChoice("Lifetime XP only", "lifetime_only"),
                OptionChoice("Restricted (admins only)", "admin_only"),
            ],
            required=False,
        ),
        oblivion_stains: Option(
            int,
            "Which Rouse results should give Oblivion stain warnings",
            choices=[
                OptionChoice("1s and 10s (RAW)", 100),
                OptionChoice("1s only", 1),
                OptionChoice("10s only", 10),
                OptionChoice("Never", 0),
            ],
            required=False,
        ),
        update_channel: Option(
            discord.TextChannel, "A channel where character updates will be posted", required=False
        ),
        add_empty_resonance: Option(
            int,
            "Whether to add Empty Resonance to the /resonance command (die result 11-12)",
            choices=[
                OptionChoice("Yes", 1),
                OptionChoice("No", 0),
            ],
            required=False,
        ),
        accessibility: Option(
            int,
            "Whether to enable or disable accessibility",
            choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
            required=False,
        ),
    ):
        """(Admin-only) Assign server-wide settings."""
        responses = []

        if experience_permissions is not None:
            response = await inconnu.settings.set_xp_permissions(ctx, experience_permissions)
            responses.append(response)

        if oblivion_stains is not None:
            response = await inconnu.settings.set_oblivion_stains(ctx, oblivion_stains)
            responses.append(response)

        if update_channel is not None:
            response = await inconnu.settings.set_update_channel(ctx, update_channel)
            responses.append(response)

        if add_empty_resonance is not None:
            add_empty = bool(add_empty_resonance)
            response = await inconnu.settings.set_empty_resonance(ctx, add_empty)
            responses.append(response)

        if accessibility is not None:
            accessibility = bool(accessibility)
            response = await inconnu.settings.set_accessibility(ctx, accessibility, "guild")
            responses.append(response)

        if responses:
            await ctx.respond("\n".join(responses))
        else:
            await ctx.respond("You didn't give me anything to set!", ephemeral=True)

    @settings.command(name="unset_update_channel")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _unset_update_channel(self, ctx):
        """Un-sets the update channel."""
        response = await inconnu.settings.set_update_channel(ctx, None)
        await ctx.respond(response)

    @settings.command(name="show")
    async def settings_show(self, ctx):
        """Display the settings in effect."""
        accessibility = "ON" if await inconnu.settings.accessible(ctx) else "OFF"
        experience_perms = await inconnu.settings.xp_permissions(ctx.guild)
        oblivion_stains = await inconnu.settings.oblivion_stains(ctx.guild) or ["Never"]
        update_channel = await inconnu.settings.update_channel(ctx.guild)
        add_empty = await inconnu.settings.add_empty_resonance(ctx.guild)

        msg = f"Accessibility mode: `{accessibility}`"
        msg += "\nOblivion Rouse stains: " + " or ".join(map(inconnu.fence, oblivion_stains))
        msg += "\n" + experience_perms
        msg += "\nUpdate channel: " + (update_channel.mention if update_channel else "`None`")
        msg += "\nEmpty Resonance in `/resonance` command: " + ("`Yes`" if add_empty else "`No`")

        embed = discord.Embed(title="Server Settings", description=msg)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon or "")
        embed.set_footer(text="Modify settings with /settings set")

        await ctx.respond(embed=embed)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(SettingsCommands(bot))
