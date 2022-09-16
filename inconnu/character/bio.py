"""character/bio.py - Create/edit/view character bios."""

import discord
from discord.ext import pages

import inconnu
from logger import Logger

__HELP_URL = "https://docs.inconnu.app/command-reference/characters/profiles#profile"


async def edit_biography(ctx, character):
    """Edit a character bio."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild, ctx.user, character)
        if character.is_pc and character.user != ctx.user.id:
            raise inconnu.errors.FetchError("You may only edit your own characters' profile.")

        modal = _CharacterBio(character, title=f"Edit Biography: {character.name}")
        await ctx.send_modal(modal)

    except (inconnu.errors.CharacterNotFoundError, inconnu.errors.FetchError) as err:
        await inconnu.utils.error(ctx, err, help=__HELP_URL)


async def show_biography(ctx, character, player, ephemeral=False):
    """Display a character's biography."""
    haven = inconnu.utils.Haven(
        ctx,
        character=character,
        owner=player,
        allow_lookups=True,
        tip="`/character bio show` `[character:CHARACTER]` `[player:PLAYER]`",
        char_filter=_has_profile,
        errmsg="None of your characters have a profile!",
        help=__HELP_URL,
    )
    character = await haven.fetch()

    if character.has_biography:
        paginator = __biography_paginator(ctx, character, haven.owner)
        await paginator.respond(ctx.interaction, ephemeral=ephemeral)
    else:
        command = f"`/character profile edit:{character.name}`"
        await ctx.respond(
            f"**{character.name}** has no profile! Set it using {command}.",
            ephemeral=True,
        )


def _has_profile(character):
    """Raises an error if the character doesn't have a profile."""
    if not character.has_biography:
        raise inconnu.errors.CharacterError(f"{character.name} doesn't have a profile!")


def __biography_paginator(ctx, character, owner):
    """Display the biography in an embed."""
    embed = inconnu.utils.VCharEmbed(
        ctx,
        character,
        owner,
        title="Biography",
        url=inconnu.profile_url(character.id),
        show_thumbnail=False,
    )

    if character.profile.biography:
        embed.add_field(
            name="History", value=character.profile.biography or "*Not set.*", inline=False
        )
    if character.profile.description:
        embed.add_field(
            name="Description & Personality",
            value=character.profile.description or "*Not set.*",
            inline=False,
        )

    embeds = []
    if character.profile.images:
        for image in character.profile.images:
            if image.startswith("https://"):
                embed_copy = embed.copy()
                embed_copy.set_image(url=image)
                embeds.append(embed_copy)

    if not embeds:
        # There weren't any valid images, so just use the original embed
        embeds.append(embed)

    Logger.debug("PROFILE: Created %s page(s) for %s", len(embeds), character.name)

    if len(embeds) > 1:
        paginator = pages.Paginator(embeds, loop_pages=True, author_check=False)
    else:
        # We don't want to show useless buttons with only 1 page
        paginator = pages.Paginator(embeds, show_disabled=False, show_indicator=False)

    return paginator


class _CharacterBio(discord.ui.Modal):
    """A character biography modal."""

    def __init__(self, character, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.character = character

        self.add_item(
            discord.ui.InputText(
                label="Biography",
                placeholder="Character biography and history. Will be publicly shown.",
                value=character.profile.biography,
                style=discord.InputTextStyle.long,
                max_length=1024,
                required=False,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Description & Personality",
                placeholder="The character's physical description. Will be publicly shown.",
                value=character.profile.description,
                style=discord.InputTextStyle.long,
                max_length=1024,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Finalize the modal."""
        biography = inconnu.utils.clean_text(self.children[0].value)
        description = inconnu.utils.clean_text(self.children[1].value)

        embed = inconnu.utils.VCharEmbed(
            interaction, self.character, description="Profile updated!"
        )
        embed.add_field(name="Want to set profile images?", value="Use `/character image upload`.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

        self.character.profile.biography = biography
        self.character.profile.description = description
        await self.character.commit()
