"""character/bio.py - Create/edit/view character bios."""

import asyncio
from urllib.parse import urlparse

import discord

import inconnu

__HELP_URL = "https://www.inconnu.app"


async def edit_biography(ctx, character):
    """Edit a character bio."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild, ctx.user, character)
        modal = _CharacterBio(character, title=f"Edit Biography: {character.name}")

        await ctx.send_modal(modal)
    except inconnu.vchar.errors.CharacterNotFoundError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)


async def show_biography(ctx, character, player, ephemeral=False):
    """Display a character's biography."""
    try:
        owner = player or ctx.user  # Don't need admin permissions for this
        tip = "`/character bio show` `[character:CHARACTER]` `[player:PLAYER]`"
        character = await inconnu.common.fetch_character(
            ctx, character, tip, __HELP_URL, owner=owner
        )

        if character.has_biography:
            embed = __biography_embed(character, owner)
            await ctx.respond(embed=embed, ephemeral=ephemeral)
        else:
            await ctx.respond(f"**{character.name}** doesn't have a biography!", ephemeral=True)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


def __biography_embed(character, owner):
    """Display the biography in an embed."""
    embed = discord.Embed(title="Biography")
    embed.set_author(name=character.name, icon_url=inconnu.get_avatar(owner))

    if character.biography:
        embed.add_field(name="History", value=character.biography or "*Not set.*", inline=False)
    if character.description:
        embed.add_field(
            name="Description & Personality",
            value=character.description or "*Not set.*",
            inline=False,
        )

    if character.image_url.startswith("https://"):
        embed.set_image(url=character.image_url)

    return embed


class _CharacterBio(discord.ui.Modal):
    """A character biography modal."""

    def __init__(self, character, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.character = character

        self.add_item(
            discord.ui.InputText(
                label="Biography",
                placeholder="Character biography and history. Will be publicly shown.",
                value=character.biography,
                style=discord.InputTextStyle.long,
                max_length=1024,
                required=False,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Description & Personality",
                placeholder="The character's physical description. Will be publicly shown.",
                value=character.description,
                style=discord.InputTextStyle.long,
                max_length=1024,
                required=False,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Image URL",
                placeholder="Will be publicly shown. Must end in .jpg, .png, etc.",
                value=character.image_url,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """Finalize the modal."""
        biography = self.children[0].value
        description = self.children[1].value
        image_url = self.children[2].value

        tasks = [
            self.character.set_biography(biography.strip()),
            self.character.set_description(description.strip()),
        ]

        if _valid_url(image_url):
            tasks.append(self.character.set_image_url(image_url))
        else:
            tasks.append(self.character.set_image_url(""))

        tasks.append(
            interaction.response.send_message(
                f"Edited **{self.character.name}'s** biography!", ephemeral=True
            )
        )
        await asyncio.gather(*tasks)


def _valid_url(url):
    """Validate a URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False
