"""commands.py - Define the commands and event handlers for the bot."""

import discord
from discord.ext import commands
from discord_ui import UI, SlashOption
from discord_ui.cogs import slash_cog, subslash_cog

import inconnu
import c_help

bot = commands.Bot(command_prefix="//", case_insensitive=True)
_ = UI(bot, slash_options={"delete_unused": True})


# Gameplay Commands

class Gameplay(commands.Cog):
    """Gameplay-based commands."""

    @commands.command(
        name="v", aliases=["roll", "r"],
        brief=c_help.ROLL_BRIEF,
        description=c_help.ROLL_DESC,
        usage=c_help.ROLL_USAGE,
        help=c_help.ROLL_HELP
    )
    async def roll(self, ctx, *, args=None):
        """Roll a dice pool, either raw or calculated from traits."""
        if args is not None:
            await inconnu.roll.parse(ctx, args)


    @slash_cog(
        name="rouse",
        options=[
            SlashOption(str, "character"),
            SlashOption(int, "count", description="The number of Rouse checks to make")
        ]
        #, guild_ids=[882411164468932609]
    )
    async def rouse(self, ctx, character=None, count=1):
        """Perform a rouse check."""
        await inconnu.rousemorse.parse(ctx, "rouse", character, count)


    @slash_cog(
        name="remorse",
        options=[SlashOption(str, "character", description="The character undergoing Remorse")]
        #, guild_ids=[882411164468932609]
    )
    async def remorse(self, ctx, character=None):
        """Perform a remorse check."""
        await inconnu.rousemorse.parse(ctx, "remorse", character)


    @slash_cog(name="resonance")
    async def resonance(self, ctx):
        """Generate a random Resonance."""
        await inconnu.resonance.generate(ctx)


# Macros!

class MacroCommands(commands.Cog, name="Macro Utilities"):
    """Macro manaagement and rolls."""

    @slash_cog(
        name="macro",
        description="Roll a macro."
        #, guild_ids=[882411164468932609]
    )
    async def macro(self, ctx):
        """Base macro command. Unreachable."""


    @slash_cog(
        name="vm",
        description="Roll a macro.",
        options=[
            SlashOption(str, "syntax",
                description="The macro to roll, plus Hunger and Difficulty",
                required=True
            ),
            SlashOption(str, "character", description="The character that owns the macro")
        ]
        #, guild_ids=[882411164468932609]
    )
    async def macro_roll(self, ctx, syntax: str, character=None):
        """Create a macro."""
        await inconnu.macros.roll.process(ctx, syntax, character)


    @subslash_cog(
        base_names="macro",
        name="create",
        description="Create a macro.",
        options=[
            SlashOption(str, "name", description="The macro's name", required=True),
            SlashOption(str, "pool", description="The dice pool", required=True),
            SlashOption(int, "difficulty", description="The default difficulty (default 0"),
            SlashOption(str, "comment", description="A comment to apply to macro rolls"),
            SlashOption(str, "character", description="The character that owns the macro")
        ]
        #, guild_ids=[882411164468932609]
    )
    async def macro_create(
        self, ctx, name: str, pool: str, difficulty=0, comment=None, character=None
    ):
        """Create a macro."""
        await inconnu.macros.create.process(ctx, name, pool, difficulty, comment, character)


    @subslash_cog(
        base_names="macro",
        name="list",
        description="List your macros.",
        options=[
            SlashOption(str, "character", description="The character to display")
        ]
        #, guild_ids=[882411164468932609]
    )
    async def macro_list(self, ctx, character=None):
        """List a character's macros."""
        await inconnu.macros.show.process(ctx, character)


    @subslash_cog(
        base_names="macro",
        name="delete",
        description="Delete a macro.",
        options=[
            SlashOption(str, "macro", description="The macro to delete", required=True),
            SlashOption(str, "character", description="The character that owns the macro")
        ]
        #, guild_ids=[882411164468932609]
    )
    async def macro_delete(self, ctx, macro: str, character=None):
        """Delete a macro."""
        await inconnu.macros.delete.process(ctx, macro, character)


# Character CRUD

class CharacterCommands(commands.Cog, name="Character Management"):
    """Character management commands."""

    @slash_cog(
        name="character",
        description="Character management commands."
        #, guild_ids=[882411164468932609]
    )
    async def character_commands(self, ctx):
        """Base character command. Unreachable."""


    @subslash_cog(
        base_names="character",
        name="create",
        description="Create a new character",
        options=[
            SlashOption(str, "name", description="The character's name", required=True),
            SlashOption(str, "splat",
                description="The character type",
                choices=[
                    {"name": "vampire", "value": "vampire"},
                    {"name": "mortal", "value": "mortal"},
                    {"name": "ghoul", "value": "ghoul"}
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
    async def delete_character(self, ctx, character: str):
        """Delete a character."""
        await inconnu.delete.prompt(ctx, character)


# Trait CRUD

class TraitCommands(commands.Cog, name="Trait Management"):
    """Trait management commands."""

    @commands.group(
        invoke_without_command=True, name="traits", aliases=["trait", "t"],
        brief = c_help.TRAITS_COMMAND_BRIEF,
        usage = c_help.TRAITS_COMMAND_USAGE,
        help = c_help.TRAITS_COMMAND_HELP
    )
    async def modify_traits(self, ctx, *, args):
        """Traits subcommand start."""
        await ctx.reply(f"Unrecognized command: `{args}`.\nSee `//help traits` for help.")


    @modify_traits.command(
        name="add",
        brief = c_help.TRAITS_ADD_BRIEF,
        usage = c_help.TRAITS_ADD_USAGE,
        help = c_help.TRAITS_ADD_HELP
    )
    async def add_trait(self, ctx, *args):
        """Add trait(s) to a character."""
        await inconnu.traits.add_update.parse(ctx, False, *args)


    @modify_traits.command(
        name="list", aliases=["show", "s"],
        brief = c_help.TRAITS_LIST_BRIEF,
        usage = c_help.TRAITS_LIST_USAGE,
        help = c_help.TRAITS_LIST_HELP
    )
    async def list_traits(self, ctx, *args):
        """Display a character's traits."""
        await inconnu.traits.show.parse(ctx, *args)


    @modify_traits.command(
        name="update",
        brief = c_help.TRAITS_UPDATE_BRIEF,
        usage = c_help.TRAITS_UPDATE_USAGE,
        help = c_help.TRAITS_UPDATE_HELP
    )
    async def update_traits(self, ctx, *args):
        """Update a character's trait(s)."""
        await inconnu.traits.add_update.parse(ctx, True, *args)


    @modify_traits.command(
        name="delete", aliases=["rm"],
        brief = c_help.TRAITS_DELETE_BRIEF,
        usage = c_help.TRAITS_DELETE_USAGE,
        help = c_help.TRAITS_DELETE_HELP
    )
    async def delete_traits(self, ctx, *args):
        """Remove traits from a character."""
        await inconnu.traits.delete.parse(ctx, *args)


# Events

@bot.event
async def on_ready():
    """Print a message letting us know the bot logged in to Discord."""
    print(f"Logged on as {bot.user}!")
    print(f"Playing on {len(bot.guilds)} servers.")
    print(discord.version_info)

    await bot.change_presence(activity=discord.Game("//help"))


@bot.event
async def on_command_error(ctx, error):
    """Handle various errors we might encounter."""
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("Sorry, this command isn't available in DMs!")
        return

    raise error


# Misc and helpers

def __status_message():
    """Sets the bot's Discord presence message."""
    servers = len(bot.guilds)
    return f"!m help | {servers} chronicles"


def setup():
    """Final bot setup."""
    bot.add_cog(Gameplay(bot))
    bot.add_cog(MacroCommands(bot))
    bot.add_cog(CharacterCommands(bot))
    bot.add_cog(TraitCommands(bot))
