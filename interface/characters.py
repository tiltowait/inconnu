"""interface/characters.py - Character management Cog."""
# pylint: disable=no-self-use

from distutils.util import strtobool

import discord
from discord import option
from discord.commands import Option, OptionChoice, SlashCommandGroup
from discord.ext import commands

import inconnu


async def _spc_options(ctx):
    """Determine whether the user can make an SPC."""
    if ctx.interaction.user.guild_permissions.administrator:
        return [OptionChoice("No", "0"), OptionChoice("Yes", "1")]
    return [OptionChoice("No", "0")]


class Characters(commands.Cog, name="Character Management"):
    """Character management commands."""

    _TEMPLATES = [
        OptionChoice("Vampire", "vampire"),
        OptionChoice("Ghoul", "ghoul"),
        OptionChoice("Mortal", "mortal"),
        OptionChoice("Thin-Blood", "thinblood"),
    ]

    @commands.user_command(name="Stats")
    async def user_characters(self, ctx, member):
        """Display the user's character(s)."""
        await inconnu.character.display_requested(ctx, None, player=member, ephemeral=True)

    character = SlashCommandGroup("character", "Character commands.")

    @character.command(name="create")
    @commands.guild_only()
    @inconnu.utils.not_on_lockdown()
    async def character_create(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "The character's name"),
        template: Option(str, "The character type", choices=_TEMPLATES),
        health: Option(int, "Health levels (4-15)", choices=inconnu.options.ratings(3, 15)),
        willpower: Option(int, "Willpower levels (3-15)", choices=inconnu.options.ratings(3, 15)),
        humanity: Option(int, "Humanity rating (0-10)", choices=inconnu.options.ratings(0, 10)),
        spc: Option(str, "(Admin only) Make an SPC", autocomplete=_spc_options, default="0"),
    ):
        """Create a new character."""
        try:
            spc = bool(strtobool(spc))
            await inconnu.character.create(
                ctx, name, template, humanity, health, willpower, spc, False
            )
        except ValueError:
            await inconnu.utils.error(ctx, f'Invalid value for `spc`: "{spc}".')

    @commands.slash_command(name="spc")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def spc_create(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "The SPC's name"),
        template: Option(str, "The character type", choices=_TEMPLATES),
        health: Option(int, "Health levels (4-15)", choices=inconnu.options.ratings(4, 15)),
        willpower: Option(int, "Willpower levels (3-15)", choices=inconnu.options.ratings(3, 15)),
        humanity: Option(int, "Humanity rating (0-10)", choices=inconnu.options.ratings(0, 10)),
    ):
        """Create an SPC character with no traits."""
        await inconnu.character.create(ctx, name, template, humanity, health, willpower, True, True)

    @character.command(name="display")
    @commands.guild_only()
    async def character_display(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character to display"),
        player: inconnu.options.player,
    ):
        """Display a character's trackers."""
        await inconnu.character.display_requested(ctx, character, player=player)

    @character.command(name="update")
    @commands.guild_only()
    async def character_update(
        self,
        ctx: discord.ApplicationContext,
        parameters: Option(str, "KEY=VALUE parameters (see /help characters)"),
        character: inconnu.options.character("The character to update"),
        player: inconnu.options.player,
    ):
        """Update a character's parameters but not the traits."""
        await inconnu.character.update(ctx, parameters, character, player=player)

    @character.command(name="adjust")
    @commands.guild_only()
    async def adjust_character(
        self,
        ctx,
        new_name: Option(str, "The character's new name", required=False),
        health: Option(
            int, "The new Health rating", choices=inconnu.options.ratings(4, 20), required=False
        ),
        willpower: Option(
            int, "The new Willpower rating", choices=inconnu.options.ratings(3, 20), required=False
        ),
        humanity: Option(
            int, "The new Humanity rating", choices=inconnu.options.ratings(0, 10), required=False
        ),
        template: Option(str, "The character's new type", choices=_TEMPLATES, required=False),
        sup_hp: Option(str, "Superficial Health (Tip: Use +X/-X)", required=False),
        agg_hp: Option(str, "Aggravated Health (Tip: Use +X/-X)", required=False),
        sup_wp: Option(str, "Superficial Willpower (Tip: Use +X/-X)", required=False),
        agg_wp: Option(str, "Aggravated Willpower (Tip: Use +X/-X)", required=False),
        stains: Option(str, "Stains (Tip: Use +X/-X)", required=False),
        unspent_xp: Option(str, "Unspent XP (Tip: Use +X/-X)", required=False),
        lifetime_xp: Option(str, "Lifetime XP (Tip: Use +X/-X)", required=False),
        hunger: Option(str, "Adjust Hunger", required=False),
        potency: Option(str, "Adjust Blood Potency", required=False),
        character: inconnu.options.character("The character to adjust"),
        player: inconnu.options.player,
    ):
        """Adjust a character's trackers. For skills and attributes, see /traits help."""

        # We will construct an update string and call the old-style parser
        parameters = []

        if new_name is not None:
            new_name = " ".join(new_name.split())  # Normalize the name first
            parameters.append(f"name={new_name}")

        if health is not None:
            parameters.append(f"health={health}")

        if willpower is not None:
            parameters.append(f"willpower={willpower}")

        if humanity is not None:
            parameters.append(f"humanity={humanity}")

        if template is not None:
            parameters.append(f"template={template}")

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
    @inconnu.utils.not_on_lockdown()
    async def character_delete(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character to delete", required=True),
    ):
        """Delete a character."""
        await inconnu.character.delete(ctx, character)

    @character.command(name="profile")
    @commands.guild_only()
    async def character_profile(
        self,
        ctx: discord.ApplicationContext,
        player: Option(
            discord.Member, "The character's owner (does not work with EDIT)", required=False
        ),
        character: inconnu.options.character("The character to show"),
        edit: inconnu.options.character("The character whose profile to edit"),
    ):
        """Show or edit a character profile."""
        if edit is not None:
            await inconnu.character.edit_biography(ctx, edit)
        else:
            await inconnu.character.show_biography(ctx, character, player=player)

    @commands.user_command(name="Profile")
    async def character_bio_context(self, ctx, member):
        """View a character's profile."""
        await inconnu.character.show_biography(ctx, None, player=member, ephemeral=True)

    # Convictions

    @character.command(name="convictions")
    @commands.guild_only()
    async def character_convictions(
        self,
        ctx: discord.ApplicationContext,
        character: inconnu.options.character("The character to show"),
        player: Option(
            discord.Member, "The character's owner (does not work with EDIT)", required=False
        ),
        edit: inconnu.options.character("The character whose convictions to set"),
    ):
        """Show a character's Convictions."""
        if edit is None:
            await inconnu.character.convictions_show(ctx, character, player=player, ephemeral=False)
        else:
            await inconnu.character.convictions_set(ctx, edit)

    @commands.user_command(name="Convictions")
    @commands.guild_only()
    async def character_convictions_context(self, ctx, member):
        """Show a character's Convictions."""
        await inconnu.character.convictions_show(ctx, None, player=member, ephemeral=True)

    # Premium

    @character.command(name="images")
    @inconnu.options.char_option("The character to display")
    @inconnu.options.player_option(description="The character's owner")
    @option(
        "controls",
        description="Who can press the pager buttons? (Default everyone)",
        choices=["Everyone", "Only me"],
        default="Everyone",
    )
    @commands.guild_only()
    async def show_character_images(
        self,
        ctx: discord.ApplicationContext,
        character: str,
        player: discord.Member,
        controls: str,
    ):
        """Display a character's images."""
        invoker_controls = controls == "Only me"
        await inconnu.character.images.display(ctx, character, invoker_controls, player=player)

    images = character.create_subgroup("image", "Character image commands")

    @images.command(name="upload")
    @commands.guild_only()
    @inconnu.utils.decorators.premium()
    async def upload_image(
        self,
        ctx: discord.ApplicationContext,
        image: Option(discord.Attachment, "The image file to upload"),
        character: inconnu.options.character(),
    ):
        """Upload an image for your character's profile."""
        await inconnu.character.images.upload(ctx, character, image)


def _check_number(label, value):
    """Check whether a given value is a number. Raise a ValueError if not."""
    if value is None:
        return False

    try:
        int(value)  # The user might have given a +/-, so we can't use .isdigit()
        return True
    except ValueError:
        raise ValueError(f"`{label}` must be a number (with or without `+/-`.") from ValueError


def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(Characters(bot))
