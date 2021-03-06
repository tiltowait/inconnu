"""character/bio.py - Create/edit/view character bios."""

import asyncio

import discord
import validators

import inconnu

__HELP_URL = "https://www.inconnu.app"


async def edit_biography(ctx, character):
    """Edit a character bio."""
    try:
        character = await inconnu.char_mgr.fetchone(ctx.guild, ctx.user, character)
        if character.user != ctx.user.id:
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
        embed = __biography_embed(character, haven.owner)
        await ctx.respond(embed=embed, ephemeral=ephemeral)
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


def __biography_embed(character, owner):
    """Display the biography in an embed."""
    embed = discord.Embed(title="Biography", url=inconnu.profile_url(character.id))
    embed.set_author(name=character.name, icon_url=inconnu.get_avatar(owner))

    if character.biography:
        embed.add_field(name="History", value=character.biography or "*Not set.*", inline=False)
    if character.description:
        embed.add_field(
            name="Description & Personality",
            value=character.description or "*Not set.*",
            inline=False,
        )

    if character.image_urls.startswith("https://"):
        embed.set_image(url=character.image_urls)

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
                value=character.image_urls,
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

        message = f"Edited **{self.character.name}'s** biography!"

        if validators.url(image_url):
            tasks.append(self.character.add_image_url(image_url))
        else:
            tasks.append(self.character.add_image_url(""))
            message += " Your image URL isn't valid and wasn't saved."

        tasks.append(interaction.response.send_message(message, ephemeral=True))
        await asyncio.gather(*tasks)
