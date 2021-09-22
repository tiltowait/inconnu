"""interface/settings.py - Settings-related commands."""

from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import slash_cog

import inconnu
from . import debug

class SettingsCommands(commands.Cog):
    """Settings-related commands."""

    # TODO: Make this available in DMs, but only for users
    @ext.check_failure_response("Accessibility settings aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @slash_cog(
        name="accessibility",
        options=[
            SlashOption(int, "enable",
                description="Whether to enable or disable accessibility",
                choices=[
                    ("Yes", 1),
                    ("No", 0)
                ],
                required=True
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def settings_base(self, ctx, enable: int):
        """Enable/disable accessibility mode for yourself."""
        enable = bool(enable)

        if inconnu.settings.set_key(ctx.author, "accessibility", enable):
            status = "enabled" if enable else "disabled"
            await ctx.respond(f"Accessibility mode **{status}**.", hidden=True)
        else:
            await ctx.respond("Error updating accessibility mode!", hidden=True)
