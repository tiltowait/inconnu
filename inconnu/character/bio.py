"""character/bio.py - Create/edit/view character bios."""

from urllib.parse import urlparse

import discord

import inconnu

__HELP_URL = "https://www.inconnu-bot.com"


async def edit_biography(ctx, character):
    """Edit a character bio."""
    character = inconnu.vchar.VChar.fetch(ctx.guild.id, ctx.user.id, character)
    modal = _CharacterBio(character, title=f"Edit Biography: {character.name}")

    await ctx.interaction.response.send_modal(modal)


async def show_biography(ctx, character, player):
    """Display a character's biography."""
    try:
        owner = ctx.user or player
        tip = "`/character bio show` `character:CHARACTER` `player:PLAYER`"
        character = await inconnu.common.fetch_character(ctx, character, tip, __HELP_URL, owner=owner)

        embed = discord.Embed(title="Biography")
        embed.set_author(name=character.name, icon_url=owner.display_avatar)

        should_show = False

        if character.biography:
            should_show = True
            embed.add_field(
                name="History",
                value=character.biography or "*Not set.*",
                inline=False
            )
        if character.description:
            should_show = True
            embed.add_field(
                name="Description & Personality",
                value=character.description or "*Not set.*",
                inline=False
            )

        if character.image_url.startswith("https://"):
            should_show = True
            embed.set_image(url=character.image_url)

        if should_show:
            await ctx.respond(embed=embed)
        else:
            await ctx.respond(f"**{character.name}** doesn't have a biography!", ephemeral=True)

    except LookupError as err:
        await inconnu.common.present_error(ctx, err, help_url=__HELP_URL)
    except inconnu.common.FetchError:
        pass


class _CharacterBio(discord.ui.Modal):
    """A character biography modal."""

    def __init__(self, character, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.character = character

        self.add_item(discord.ui.InputText(
            label="Biography",
            placeholder="Character biography and history.",
            value=character.biography,
            style=discord.InputTextStyle.long,
            max_length=1024,
            required=False
        ))
        self.add_item(discord.ui.InputText(
            label="Description & Personality",
            placeholder="The character's physical description.",
            value=character.description,
            style=discord.InputTextStyle.long,
            max_length=1024,
            required=False
        ))
        self.add_item(discord.ui.InputText(
            label="Image URL",
            placeholder="The character's face claim.",
            value=character.image_url,
            required=False,
        ))


    async def callback(self, interaction: discord.Interaction):
        """Finalize the modal."""
        biography = self.children[0].value
        description = self.children[1].value
        image_url = self.children[2].value

        self.character.biography = biography.strip()
        self.character.description = description.strip()

        if _valid_url(image_url):
            self.character.image_url = image_url
        else:
            self.character.image_url = ""

        await interaction.response.send_message(
            f"Edited **{self.character.name}'s** biography!",
            ephemeral=True
        )


def _valid_url(url):
    """Validate a URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False
