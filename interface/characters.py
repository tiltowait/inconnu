"""interface/characters.py - Character management Cog."""

from discord.ext import commands
from discord_ui import SlashOption
from discord_ui.cogs import slash_cog, subslash_cog

import inconnu


class Characters(commands.Cog, name="Character Management"):
    """Character management commands."""

    @slash_cog(
        name="character",
        description="Character management commands."
        #, guild_ids=[882411164468932609]
    )
    @commands.guild_only()
    async def character_commands(self, ctx):
        """Base character command. Unreachable."""


    @subslash_cog(
        base_names="character",
        name="create",
        description="Create a new character",
        options=[
            SlashOption(str, "name", description="The character's name", required=True),
            SlashOption(int, "splat",
                description="The character type",
                choices=[
                    {"name": "vampire", "value": 0},
                    {"name": "mortal", "value": 1},
                    {"name": "ghoul", "value": 2}
                ],
                required=True
            ),
            SlashOption(int, "humanity",
                description="Humanity rating (0-10)",
                choices=[{"name": str(n), "value": n} for n in range(0, 11)],
                required=True
            ),
            SlashOption(int, "health",
                description="Health levels (4-15)",
                choices=[{"name": str(n), "value": n} for n in range(4, 16)],
                required=True
            ),
            SlashOption(int, "willpower",
                description="Willpower levels (3-15)",
                choices=[{"name": str(n), "value": n} for n in range(3, 16)],
                required=True
            )
        ]
        #, guild_ids=[882411164468932609]
    )
    @commands.guild_only()
    async def new_character(
        self, ctx, name: str, splat: str, humanity: int, health: int, willpower: int
    ):
        """Create a new character."""
        await inconnu.newchar.create(ctx, name, splat, humanity, health, willpower)


    @subslash_cog(
        base_names="character",
        name="display",
        description="List all of your characters or show details about one character.",
        options=[SlashOption(str, "character", description="A character to display")]
        #, guild_ids=[882411164468932609]
    )
    @commands.guild_only()
    async def display_character(self, ctx, character=None):
        """Display a character's basic traits"""
        await inconnu.display.parse(ctx, character)


    @subslash_cog(
        base_names="character",
        name="update",
        description="Update a character's trackers.",
        options=[
            SlashOption(str, "parameters", description="KEY=VALUE parameters", required=True),
            SlashOption(str, "character", description="The character to update")
        ]
    )
    @commands.guild_only()
    async def update_character(self, ctx, parameters: str, character=None):
        """Update a character's parameters but not the traits."""
        await inconnu.update.parse(ctx, parameters, character)


    @subslash_cog(
        base_names="character",
        name="delete",
        options=[
            SlashOption(str, "character", description="The character to delete", required=True)
        ]
        #, guild_ids=[882411164468932609]
    )
    @commands.guild_only()
    async def delete_character(self, ctx, character: str):
        """Delete a character."""
        await inconnu.delete.prompt(ctx, character)


