"""interface/settings.py - Settings-related commands."""

from discord.ext import commands
from discord_ui import SlashOption
from discord_ui.cogs import slash_cog

import inconnu
from . import debug


async def _available_scopes(ctx):
    """Determine the available settings scopes."""
    if ctx.author.guild_permissions.administrator:
        return [("Self only", "user"), ("Entire server", "server")]
    return [("Self only", "user")]


class SettingsCommands(commands.Cog):
    """Settings-related commands."""

    @slash_cog(
        name="settings",
        options=[
            SlashOption(int, "oblivion_stains",
                description="Which Rouse results should give stain warnings",
                choices=[
                    ("1s and 10s (RAW)", 100),
                    ("1s only", 1),
                    ("10s only", 10),
                    ("None", 0)
                ]
            ),
            SlashOption(str, "scope",
                description="Set for yourself or the entire server",
                autocomplete=True, choice_generator=_available_scopes
            ),
        ],
        guild_ids=debug.WHITELIST
    )
    async def settings(self, ctx, oblivion_stains=None, scope="user"):
        """Assign various user- or server-wide settings."""
        error_msg = "Sorry, you must be a server administrator to do this."

        if scope == "guild" and not ctx.author.guild_permissions.administrator:
            await ctx.respond(error_msg, hidden=True)
            return

        responses = []

        if oblivion_stains is not None:
            if not ctx.author.guild_permissions.administrator:
                await ctx.respond(error_msg, hidden=True)
                return

            response = "Set **Oblivion Rouse stains** to "
            if oblivion_stains == 100:
                oblivion_stains = [1, 10]
                response += "`1` and `10`."
            elif oblivion_stains == 0:
                oblivion_stains = []
                response = "**Oblivion Rouses** give `no` stains."
            else:
                oblivion_stains = [oblivion_stains]
                response += f"`{oblivion_stains[0]}`."

            inconnu.settings.set_key(ctx.guild, "oblivion_stains", oblivion_stains)
            responses.append(response)

        await ctx.respond("\n".join(responses))


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
                autocomplete=True, choice_generator=_available_scopes
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def accessibility(self, ctx, enable: int, scope="user"):
        """Enable/disable accessibility mode for yourself or the server."""
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
