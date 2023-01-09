"""Character image uploading."""

import discord

import inconnu
from inconnu import api
from inconnu.utils.haven import haven
from logger import Logger

__HELP_URL = "https://docs.inconnu.app/guides/premium/character-images"
VALID_EXTENSIONS = [".png", ".webp", ".jpg", ".jpeg"]


@haven(__HELP_URL)
async def upload_image(ctx: discord.ApplicationContext, character, image: discord.Attachment):
    """Upload an image. Only premium users can use this feature."""
    if not valid_url(image.url):
        embed = inconnu.utils.ErrorEmbed(
            ctx.user,
            "This is not a valid image file!",
            ("Allowed extensions", ", ".join(VALID_EXTENSIONS)),
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

    if not ctx.interaction.response.is_done():
        # If we responded already, there's no chance of timeout; also we can't
        # defer if we've responded, so ...
        await ctx.defer(ephemeral=True)

    try:
        aws_image_url = await api.upload_faceclaim(character, image.url)
        Logger.info("IMAGES: %s: Uploaded new image to %s", character.name, aws_image_url)

        character.profile.images.append(aws_image_url)

        embed = inconnu.utils.VCharEmbed(
            ctx,
            character,
            title="Image uploaded!",
            show_thumbnail=False,
        )
        embed.set_image(url=aws_image_url)
        embed.set_footer(text="View your images with /character images.")

        await ctx.respond(embed=embed, ephemeral=True)
        await character.commit()

        # We maintain a log of all image uploads to protect ourself against
        # potential legal claims if someone uploads something illegal
        await inconnu.db.upload_log.insert_one(
            {
                "guild": ctx.guild.id,
                "user": ctx.user.id,
                "charid": character.pk,
                "url": aws_image_url,
                "deleted": False,
                "timestamp": discord.utils.utcnow(),
            }
        )

    except inconnu.errors.ApiError:
        await inconnu.utils.error(ctx, "Unable to process image. Please try again later.")


def valid_url(url: str) -> bool:
    """Check whether a URL is a valid image URL."""
    url = url.lower()
    Logger.debug("IMAGES: Checking validity of %s", url)

    for extension in VALID_EXTENSIONS:
        if url.endswith(extension):
            return True
    return False
