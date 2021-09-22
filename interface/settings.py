"""interface/settings.py - Settings-related commands."""

from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import slash_cog

import inconnu
from . import debug

class SettingsCommands(commands.Cog):
    """Settings-related commands."""

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
            ),
            SlashOption(str, "scope",
                description="Set for yourself or the entire server",
                choices=[
                    ("Self only", "user"),
                    ("Entire server", "server")
                ]
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def settings_base(self, ctx, enable: int, scope="user"):
        """Enable/disable accessibility mode for yourself."""
        enable = bool(enable)

        if scope == "user":
            did_set = inconnu.settings.set_key(ctx.author, "accessibility", enable)
        else:
            if ctx.author.guild_permissions.administrator:
                did_set = inconnu.settings.set_key(ctx.guild, "accessibility", enable)
            else:
                await ctx.respond("Sorry, you aren't a server administrator.", hidden=True)
                return

        if did_set and scope == "user":
            if enable:
                await ctx.respond("Accessibility mode enabled.", hidden=True)
            else:
                await ctx.respond(
                    "Accessibility mode disabled. Note that server settings may override this.",
                    hidden=True
                )
        elif did_set and scope == "server":
            if enable:
                await ctx.respond("Accessibility mode enabled server-wide.")
            else:
                await ctx.respond(
                    "Accessibility mode disabled server-wide. User preferences can override."
                )
        else:
            await ctx.respond("Error updating accessibility mode!", hidden=True)
