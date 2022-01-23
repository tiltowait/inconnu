"""interface/characters.py - Character management Cog."""

import discord
from discord.ext import commands
from discord_ui import ext, SlashOption
from discord_ui.cogs import subslash_command, context_command

import inconnu
from . import debug

# Unused due to Discord API issues
async def _spc_options(_, ctx):
    """Determine whether the user can make an SPC."""
    if ctx.author.guild_permissions.administrator:
        return [("No", "0"), ("Yes", "1")]
    return [("No", "0")]


class Characters(commands.Cog, name="Character Management"):
    """Character management commands."""

    @context_command(
        name="Characters",
        type="user",
        guild_ids=debug.WHITELIST
    )
    async def user_characters(self, ctx, user):
        """Display the user's character(s)."""
        await self.display_character(ctx, None, user)


    @ext.check_failed("Characters aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_command(
        base_names="character",
        name="create",
        description="Create a new character",
        options=[
            SlashOption(str, "name", description="The character's name", required=True),
            SlashOption(str, "splat",
                description="The character type",
                choices=[
                    ("vampire", "vampire"),
                    ("ghoul", "ghoul"),
                    ("mortal", "mortal")
                ],
                required=True
            ),
            SlashOption(int, "humanity",
                description="Humanity rating (0-10)",
                choices=[(str(n), n) for n in range(0, 11)],
                required=True
            ),
            SlashOption(int, "health",
                description="Health levels (4-15)",
                choices=[(str(n), n) for n in range(4, 16)],
                required=True
            ),
            SlashOption(int, "willpower",
                description="Willpower levels (3-15)",
                choices=[(str(n), n) for n in range(3, 16)],
                required=True
            ),
            SlashOption(int, "spc",
                description="(Admin only) Make an SPC",
                #autocomplete=True, choice_generator=_spc_options
                choices=[("No", 0), ("Yes", 1)]
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def new_character(
        self, ctx, name: str, splat: str, humanity: int, health: int, willpower: int, spc=0
    ):
        """Create a new character."""
        await inconnu.character.create(ctx, name, splat, humanity, health, willpower, bool(spc))


    @ext.check_failed("Characters aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_command(
        base_names="character",
        name="display",
        description="List all of your characters or show details about one character.",
        options=[
            SlashOption(str, "character", description="A character to display",
                autocomplete=True, choice_generator=inconnu.available_characters
            ),
            SlashOption(discord.Member, "player",
                description="The player who owns the character (admin only)"
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def display_character(self, ctx, character=None, player=None):
        """Display a character's basic traits"""
        await inconnu.character.display_requested(ctx, character, player=player)


    @ext.check_failed("Characters aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_command(
        base_names="character",
        name="update",
        description="Update a character's trackers.",
        options=[
            SlashOption(str, "parameters", description="KEY=VALUE parameters", required=True),
            SlashOption(str, "character", description="The character to update",
                autocomplete=True, choice_generator=inconnu.available_characters
            ),
            SlashOption(discord.Member, "player",
                description="The player who owns the character (admin only)"
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def update_character(self, ctx, parameters: str, character=None, player=None):
        """Update a character's parameters but not the traits."""
        await inconnu.character.update(ctx, parameters, character, player=player)


    @ext.check_failed("Characters aren't available in DMs.", hidden=True)
    @commands.guild_only()
    @subslash_command(
        base_names="character",
        name="delete",
        description="Delete a character.",
        options=[
            SlashOption(str, "character", description="The character to delete", required=True,
                autocomplete=True, choice_generator=inconnu.available_characters
            )
        ]
        , guild_ids=debug.WHITELIST
    )
    async def delete_character(self, ctx, character: str):
        """Delete a character."""
        await inconnu.character.delete(ctx, character)
