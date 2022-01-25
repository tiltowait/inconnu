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

    _SPLATS = [("vampire", "vampire"), ("ghoul", "ghoul"), ("mortal", "mortal")]

    def __init__(self, bot):
        self.bot = bot


    @context_command(
        name="Characters",
        type="user",
        guild_ids=debug.WHITELIST
    )
    async def user_characters(self, ctx, user):
        """Display the user's character(s)."""
        await self.display_character(ctx, None, user, hidden=True)


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
                choices=_SPLATS,
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
    async def display_character(self, ctx, character=None, player=None, hidden=False):
        """Display a character's basic traits"""
        await inconnu.character.display_requested(ctx, character, player=player, hidden=hidden)


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
        name="adjust",
        options=[
            SlashOption(str, "new_name", description="The character's new name", required=False),
            SlashOption(int, "health",
                description="The new Health rating",
                min_value=4, max_value=20,
                required=False
            ),
            SlashOption(int, "willpower",
                description="The new Willpower rating",
                min_value=3, max_value=20,
                required=False
            ),
            SlashOption(int, "humanity",
                description="The new Humanity rating",
                min_value=0, max_value=10,
                required=False
            ),
            SlashOption(str, "splat",
                description="The character's new type",
                choices=_SPLATS,
                required=False
            ),
            SlashOption(str, "sup_hp", description="Adjust Superficial Health", required=False),
            SlashOption(str, "agg_hp", description="Adjust Aggravated Health", required=False),
            SlashOption(str, "sup_wp", description="Adjust Superficial Willpower", required=False),
            SlashOption(str, "agg_wp", description="Adjust Aggravated Willpower", required=False),
            SlashOption(str, "stains", description="Adjust stains", required=False),
            SlashOption(str, "unspent_xp", description="Adjust unspent XP", required=False),
            SlashOption(str, "lifetime_xp", description="Adjust lifetime XP", required=False),
            SlashOption(str, "hunger", description="Adjust Hunger", required=False),
            SlashOption(str, "potency", description="Adjust Blood Potency", required=False),
            SlashOption(str, "character", description="A character to display",
                autocomplete=True, choice_generator=inconnu.available_characters
            ),
            SlashOption(discord.Member, "player",
                description="The player who owns the character (admin only)"
            )
        ],
        guild_ids=debug.WHITELIST
    )
    async def adjust_character(self, ctx,
        new_name=None,
        health=None,
        willpower=None,
        humanity=None,
        splat=None,
        sup_hp=None,
        agg_hp=None,
        sup_wp=None,
        agg_wp=None,
        stains=None,
        unspent_xp=None,
        lifetime_xp=None,
        hunger=None,
        potency=None,
        character=None,
        player=None
    ):
        """Adjust a character's trackers. For skills and attributes, see /traits help."""

        # We will construct an update string and call the old-style parser
        parameters = []

        if new_name is not None:
            new_name = "_".join(new_name.split()) # Normalize the name first
            parameters.append(f"name={new_name}")

        if health is not None:
            parameters.append(f"health={health}")

        if willpower is not None:
            parameters.append(f"willpower={willpower}")

        if humanity is not None:
            parameters.append(f"humanity={humanity}")

        if splat is not None:
            parameters.append(f"splat={splat}")

        # The rest of these are adjustments, but they must be able to convert into an int
        try:
            if _check_number("sup_hp", sup_hp):
                parameters.append(f"sh={sup_hp}")

            if _check_number("agg_hp", agg_hp):
                parameters.append(f"ah={agg_hp}")

            if _check_number("sup_wp", sup_wp):
                parameters.append(f"sw={sup_wp}")

            if _check_number("agg_wp", agg_wp):
                parameters.append(f"aw={agg_wp}")

            if _check_number("stains", stains):
                parameters.append(f"stains={stains}")

            if _check_number("lifetime_xp", lifetime_xp):
                parameters.append(f"lxp={lifetime_xp}")

            if _check_number("unspent_xp", unspent_xp):
                parameters.append(f"uxp={unspent_xp}")

            if _check_number("hunger", hunger):
                parameters.append(f"hunger={hunger}")

            if _check_number("potency", potency):
                parameters.append(f"potency={potency}")

            # Combine the parameters and send them off to the updater
            parameters = " ".join(parameters)
            await inconnu.character.update(ctx, parameters, character, player=player)

        except ValueError as err:
            await ctx.respond(err, hidden=True)


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


def _check_number(label, value):
    """Check whether a given value is a number. Raise a ValueError if not."""
    if value is None:
        return False

    try:
        int(value) # The user might have given a +/-, so we can't use .isdigit()
        return True
    except ValueError:
        raise ValueError(f"`{label}` must be a number (with or without `+/-`.") from ValueError
