"""interface/settings.py - Settings-related commands."""

import discord
from discord import option
from discord.commands import OptionChoice, SlashCommandGroup, slash_command
from discord.ext import commands

import inconnu
from ctx import AppCtx


class SettingsCommands(commands.Cog):
    """Settings-related commands."""

    @slash_command()
    @option(
        "scope",
        description="Show/edit settings for yourself or the server.",
        choices=[
            OptionChoice("Yourself", "self"),
            OptionChoice("Server", "guild"),
        ],
    )
    async def seppuku(self, ctx: AppCtx, scope: str):
        """Adjust user/server settings."""
        await inconnu.edit_settings(ctx, scope)

    @slash_command()
    @option("enable", description="Enable accessibility mode for yourself")
    async def accessibility(
        self,
        ctx: discord.ApplicationContext,
        enable: bool,
    ):
        """Enable or disable accessibility mode for yourself."""
        response = await inconnu.settings.set_accessibility(ctx, enable, "user")
        await ctx.respond(response)

    settings = SlashCommandGroup(
        "settings",
        "Server settings commands.",
        contexts={discord.InteractionContextType.guild},
    )

    @settings.command(name="set")
    @commands.has_permissions(administrator=True)
    @option(
        "experience_permissions",
        description="Whether users should be allowed to edit their XP totals.",
        choices=[
            OptionChoice("Unrestricted", "unrestricted"),
            OptionChoice("Unspent XP only", "unspent_only"),
            OptionChoice("Lifetime XP only", "lifetime_only"),
            OptionChoice("Restricted (admins only)", "admin_only"),
        ],
        required=False,
    )
    @option(
        "oblivion_stains",
        description="Which Rouse results should give Oblivion stain warnings",
        choices=[
            OptionChoice("1s and 10s (RAW)", 100),
            OptionChoice("1s only", 1),
            OptionChoice("10s only", 10),
            OptionChoice("Never", 0),
        ],
        required=False,
    )
    @option(
        "update_channel",
        description="A channel where character updates will be posted",
        required=False,
    )
    @option(
        "changelog_channel",
        description="A channel where edited Roleposts will be logged",
        required=False,
    )
    @option(
        "deletion_channel",
        description="A channel where deleted Roleposts will be logged",
        required=False,
    )
    @option(
        "add_empty_resonance",
        description="Whether to add Empty Resonance to the /resonance command (die result 11-12)",
        choices=[
            OptionChoice("Yes", 1),
            OptionChoice("No", 0),
        ],
        required=False,
    )
    @option(
        "max_hunger",
        description=(
            "Maximum Hunger rating in rolls (Only affects /vr. Characters still "
            "max out at Hunger 5.)"
        ),
        choices=[5, 10],
        required=False,
    )
    @option(
        "accessibility",
        description="Whether to enable or disable accessibility",
        choices=[OptionChoice("Yes", 1), OptionChoice("No", 0)],
        required=False,
    )
    async def set(
        self,
        ctx: discord.ApplicationContext,
        experience_permissions: str,
        oblivion_stains: int,
        update_channel: discord.TextChannel,
        changelog_channel: discord.TextChannel,
        deletion_channel: discord.TextChannel,
        add_empty_resonance: int,
        max_hunger: int,
        accessibility: int,
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

        if changelog_channel is not None:
            response = await inconnu.settings.set_changelog_channel(ctx, changelog_channel)
            responses.append(response)

        if deletion_channel is not None:
            response = await inconnu.settings.set_deletion_channel(ctx, deletion_channel)
            responses.append(response)

        if add_empty_resonance is not None:
            add_empty = bool(add_empty_resonance)
            response = await inconnu.settings.set_empty_resonance(ctx, add_empty)
            responses.append(response)

        if max_hunger is not None:
            response = await inconnu.settings.set_max_hunger(ctx, max_hunger)
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
        changelog_channel = await inconnu.settings.changelog_channel(ctx.guild)
        deletion_channel = await inconnu.settings.deletion_channel(ctx.guild)
        add_empty = await inconnu.settings.add_empty_resonance(ctx.guild)

        msg = f"Accessibility mode: `{accessibility}`"
        msg += "\nOblivion Rouse stains: " + " or ".join(map(inconnu.fence, oblivion_stains))
        msg += "\n" + experience_perms
        msg += "\nUpdate channel: " + (update_channel.mention if update_channel else "`None`")
        msg += "\nChangelog channel: " + (
            f"<#{changelog_channel}>" if changelog_channel else "`None`"
        )
        msg += "\nDeletion channel: " + (f"<#{deletion_channel}>" if deletion_channel else "`None`")
        msg += "\nEmpty Resonance in `/resonance` command: " + ("`Yes`" if add_empty else "`No`")

        embed = discord.Embed(title="Server Settings", description=msg)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon or "")
        embed.set_footer(text="Modify settings with /settings set")

        await ctx.respond(embed=embed)


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(SettingsCommands(bot))
