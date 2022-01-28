"""interface/characters.py - Character management Cog."""

from distutils.util import strtobool

import discord
from discord.commands import Option, OptionChoice, SlashCommandGroup
from discord.ext import commands

import inconnu

# Unused due to Discord API issues
async def _spc_options(ctx):
    """Determine whether the user can make an SPC."""
    if ctx.interaction.user.guild_permissions.administrator:
        return [OptionChoice("No", "0"), OptionChoice("Yes", "1")]
    return [OptionChoice("No", "0")]


def _ratings(low, high):
    """Creates a list of OptionChoices within the given range, inclusive."""
    return [OptionChoice(str(n), n) for n in range(low, high + 1)]


class Characters(commands.Cog, name="Character Management"):
    """Character management commands."""

    _SPLATS = ["vampire", "ghoul", "mortal"]
    _CHARACTER_OPTION = Option(str, "The character to use",
        autocomplete=inconnu.available_characters,
        required=False
    )
    _PLAYER_OPTION = Option(discord.Member, "The character's owner (admin only)", required=False)


    @commands.user_command(name="Characters")
    async def user_characters(self, ctx, user):
        """Display the user's character(s)."""
        await self.character_display(ctx, None, user, ephemeral=True)


    character = SlashCommandGroup("character", "Character commands.")

    @character.command(name="create")
    @commands.guild_only()
    async def character_create(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "The character's name"),
        splat: Option(str, "The character type", choices=_SPLATS),
        humanity: Option(int, "Humanity rating (0-10)", choices=_ratings(0, 10)),
        health: Option(int, "Health levels (4-15)", choices=_ratings(4, 15)),
        willpower: Option(int, "Willpower levels (3-15)", choices=_ratings(3, 15)),
        spc: Option(str, "(Admin only) Make an SPC", autocomplete=_spc_options, default="0")
    ):
        """Create a new character."""
        spc = bool(strtobool(spc))
        await inconnu.character.create(ctx, name, splat, humanity, health, willpower, spc)


    @character.command(name="display")
    @commands.guild_only()
    async def character_display(
        self,
        ctx: discord.ApplicationContext,
        character: _CHARACTER_OPTION,
        player: _PLAYER_OPTION,
        ephemeral=False
    ):
        """Display a character's trackers."""
        await inconnu.character.display_requested(ctx, character, player=player, ephemeral=ephemeral)


    @character.command(name="update")
    @commands.guild_only()
    async def character_update(
        self,
        ctx: discord.ApplicationContext,
        parameters: Option(str, "KEY=VALUE parameters (see /character help)"),
        character: _CHARACTER_OPTION,
        player: _PLAYER_OPTION
    ):
        """Update a character's parameters but not the traits."""
        await inconnu.character.update(ctx, parameters, character, player=player)


    @character.command(name="adjust")
    @commands.guild_only()
    async def adjust_character(self, ctx,
        new_name: Option(str, "The character's new name", required=False),
        health: Option(int, "The new Health rating", choices=_ratings(4, 20), required=False),
        willpower: Option(int, "The new Willpower rating", choices=_ratings(3, 20), required=False),
        humanity: Option(int, "The new Humanity rating", choices=_ratings(0, 10), required=False),
        splat: Option(str, "The character's new type", choices=_SPLATS, required=False),
        sup_hp: Option(str, "Adjust Superficial Health", required=False),
        agg_hp: Option(str, "Adjust Aggravated Health", required=False),
        sup_wp: Option(str, "Adjust Superficial Willpower", required=False),
        agg_wp: Option(str, "Adjust Aggravated Willpower", required=False),
        stains: Option(str, "Adjust stains", required=False),
        unspent_xp: Option(str, "Adjust unspent XP", required=False),
        lifetime_xp: Option(str, "Adjust lifetime XP", required=False),
        hunger: Option(str, "Adjust Hunger", required=False),
        potency: Option(str, "Adjust Blood Potency", required=False),
        character: _CHARACTER_OPTION,
        player: _PLAYER_OPTION
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
            await ctx.respond(err, ephemeral=True)


    @character.command(name="delete")
    @commands.guild_only()
    async def character_delete(
        self,
        ctx: discord.ApplicationContext,
        character: _CHARACTER_OPTION
    ):
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
